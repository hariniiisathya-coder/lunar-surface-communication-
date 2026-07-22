"""
Dielectric sensitivity diagnostic -- addresses three checks:

  Check 1: distribution of specular grazing angles across the map. If all
           near-grazing (<~2 deg), eps is geometrically suppressed here.
  Check 2: force crater-wall ROCK permittivity (eps' = 6, 8), not just the
           mare/highlands range, to see if the big jump moves coverage.
  Check 3: bypass the (extrapolated/shaky) Siegler map -- set eps' by hand to
           2.5, 3.0, 3.5, 6.0 -- to separate 'grazing suppresses eps' (physics)
           from 'the map barely varied here' (data artifact).

Run from project root:  python dielectric_sensitivity.py
"""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS = 53.0, 2.0, -106.0


def rho_for_eps(eps):
    """Density that yields a given real permittivity via eps' = 1.919**rho."""
    return np.log(eps) / np.log(1.919)


def specular_grazing_angle_deg(dh, tx_elev, rx_elev):
    """Grazing angle (deg from surface) of the ground-reflected ray."""
    # flat-earth two-ray: reflected ray grazing angle = atan((h_tx+h_rx)/d)
    return np.degrees(np.arctan((tx_elev + rx_elev) / dh)) if dh > 0 else 90.0


def run(dem, px, tx, freq_hz, eps_forced=None):
    """Coverage with reflection permittivity forced to eps_forced (or default
    regolith rho=1.5 if None). Returns (covered_pct, grazing_angles list)."""
    ny, nx = dem.shape
    rho = rho_for_eps(eps_forced) if eps_forced else 1.50
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    covered = total = 0
    angles = []
    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx:
                covered += 1; total += 1; continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            if los[i, j]:
                # record grazing angle (LOS reflection pixels only)
                angles.append(specular_grazing_angle_deg(dh, H_TX, H_RX))
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, freq_hz, rho))
            else:
                d3d = np.hypot(dh, rx_elev - tx_elev)
                pl = float(friis.fspl_db(d3d, freq_hz))
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, freq_hz))
            margin = friis.link_margin_db(friis.received_power_dbm(EIRP, pl, GRX), SENS)
            total += 1
            if margin > 0:
                covered += 1
    return 100 * covered / total, angles


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, TX {tx}, elev {dem[tx]:.1f} m\n")

    # --- Check 1: grazing angle distribution (from the default run) ---
    base_pct, angles = run(dem, px, tx, FREQ_HZ, eps_forced=None)
    angles = np.array(angles)
    print("CHECK 1 -- specular grazing-angle distribution (LOS pixels):")
    print(f"  n={len(angles)}, min={angles.min():.2f} deg, median={np.median(angles):.2f} deg, "
          f"max={angles.max():.2f} deg")
    for thr in [2, 5, 10, 20]:
        frac = 100 * np.mean(angles > thr)
        print(f"  fraction with grazing angle > {thr:2d} deg: {frac:.1f}%")
    print()

    # --- Checks 2 & 3: forced-epsilon sweep ---
    print("CHECKS 2&3 -- coverage with reflection eps' forced by hand:")
    print(f"  {'eps_real':>10s} {'covered %':>10s} {'vs eps=2.5':>12s}")
    ref = None
    for eps in [2.5, 3.0, 3.5, 6.0, 8.0]:
        pct, _ = run(dem, px, tx, FREQ_HZ, eps_forced=eps)
        if ref is None:
            ref = pct
        tag = "  <-- rock" if eps >= 6 else ""
        print(f"  {eps:>10.1f} {pct:>9.1f}% {pct-ref:>11.1f}%{tag}")
    print()
    print("Interpretation:")
    print("  * If coverage is flat across ALL eps (incl. 6-8), the flatness is")
    print("    the grazing-angle geometry (Check 1 should show near-grazing).")
    print("  * If coverage MOVES at eps=6-8 but not 2.5-3.5, then rock at crater")
    print("    walls matters even though mare/highlands variation does not.")
    print("  * If Check 1 shows a tail of steep angles, eps matters there and the")
    print("    map-averaged 0% was masking it.")


if __name__ == "__main__":
    main()

"""
Stress-test: does dielectric (eps' = 2.5 vs 8.0) ever move the COVERAGE
PERCENTAGE under a tighter link budget?

v2 showed margin sensitivity to eps is real (up to 3 dB) but every LOS pixel
sat 50-90 dB above threshold with the nominal Edwards (2023) budget (EIRP=53,
sens=-106), so nothing near the boundary ever existed.

Here we sweep the EFFECTIVE budget (by cutting EIRP) across several stressed
values and, at EACH one, compute coverage% for eps=2.5 and eps=8.0 and report
the difference. This finds whether/where dielectric sensitivity becomes
visible in the coverage metric, rather than guessing one value.

Run from project root:  python link_budget_stress_test.py
"""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
EIRP_NOMINAL = 53.0


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def coverage_pct(dem, px, tx, los, eirp, eps):
    ny, nx = dem.shape
    rho = rho_for_eps(eps)
    tx_elev = dem[tx] + H_TX
    covered = total = 0
    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx:
                covered += 1; total += 1; continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            if los[i, j]:
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ_HZ, rho))
            else:
                d3d = np.hypot(dh, rx_elev - tx_elev)
                pl = float(friis.fspl_db(d3d, FREQ_HZ))
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, FREQ_HZ))
            margin = friis.link_margin_db(friis.received_power_dbm(eirp, pl, GRX), SENS)
            total += 1
            if margin > 0:
                covered += 1
    return 100 * covered / total


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    print(f"DEM {dem.shape}, TX {tx}, elev {dem[tx]:.1f} m\n")

    # cut EIRP by increasing amounts to push the coverage boundary INTO the
    # 2 km subset (nominal budget covers the whole subset with huge margin)
    cuts = [0, 20, 40, 55, 60, 65, 70, 75, 80]
    print(f"{'EIRP cut':>9s} {'eff EIRP':>9s} {'cov% eps=2.5':>13s} {'cov% eps=8.0':>13s} {'delta':>8s}")
    print("-" * 58)
    for cut in cuts:
        eirp = EIRP_NOMINAL - cut
        c_lo = coverage_pct(dem, px, tx, los, eirp, 2.5)
        c_hi = coverage_pct(dem, px, tx, los, eirp, 8.0)
        print(f"{cut:>8d}dB {eirp:>8.1f} {c_lo:>12.1f}% {c_hi:>12.1f}% {c_hi-c_lo:>7.1f}%")


if __name__ == "__main__":
    main()

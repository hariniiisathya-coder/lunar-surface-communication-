"""
Evidence script: reproduces the S-band vs Ka-band dielectric-sensitivity
comparison at fine (0.2 dB) EIRP resolution.

For each band, computes coverage % across a sweep of EIRP values, once with
regolith permittivity (eps'=2.5) and once with crater-wall-rock permittivity
(eps'=8.0), then reports the MAXIMUM absolute difference in coverage %
found anywhere in the sweep.

Path loss (two-ray for LOS pixels, FSPL+Deygout for NLOS pixels) is
precomputed once per band/eps -- it does not depend on EIRP -- so sweeping
EIRP at fine resolution afterwards is cheap.

Run from the project root:  python coverage_delta_evidence.py
"""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
EPS_LOW, EPS_HIGH = 2.5, 8.0
BANDS = {"S": 2.5e9, "Ka": 27.0e9}
EIRP_RANGE_DBM = np.arange(-30, 61, 0.2)   # fine 0.2 dB resolution


def rho_for_eps(eps):
    """Density that yields real permittivity eps via eps' = 1.919**rho."""
    return np.log(eps) / np.log(1.919)


def precompute_path_loss(dem, px, tx, freq_hz, eps_values):
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    ii, jj = np.mgrid[0:ny, 0:nx]
    dh = np.hypot(ii - tx[0], jj - tx[1]) * px

    # NLOS path loss (FSPL + Deygout) is eps-independent -- compute once
    nlos_pl = np.full((ny, nx), np.nan)
    for (i, j) in np.argwhere(~los):
        if (i, j) == tx:
            continue
        rx_elev = dem[i, j] + H_RX
        d3d = np.hypot(dh[i, j], rx_elev - tx_elev)
        pl = float(friis.fspl_db(d3d, freq_hz))
        h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
        pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, freq_hz))
        nlos_pl[i, j] = pl

    pl_by_eps = {}
    los_no_tx = los.copy()
    los_no_tx[tx] = False
    for eps in eps_values:
        rho = rho_for_eps(eps)
        pl = np.full((ny, nx), np.nan)
        pl[los_no_tx] = two_ray.path_loss_db(dh[los_no_tx], H_TX, H_RX, freq_hz, rho)
        pl[~los] = nlos_pl[~los]
        pl_by_eps[eps] = pl
    return pl_by_eps


def coverage_curve(pl, eirp_range):
    valid = np.isfinite(pl)
    n_valid = int(np.sum(valid)) + 1  # +1 for the TX pixel (always covered)
    out = np.empty(len(eirp_range))
    for k, eirp in enumerate(eirp_range):
        prx = friis.received_power_dbm(eirp, pl, GRX)
        margin = friis.link_margin_db(prx, SENS)
        covered = int(np.nansum(margin > 0)) + 1
        out[k] = 100 * covered / n_valid
    return out


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, TX {tx}, elev {dem[tx]:.1f} m")
    print(f"eps'={EPS_LOW} vs eps'={EPS_HIGH}, EIRP swept {EIRP_RANGE_DBM[0]} to "
          f"{EIRP_RANGE_DBM[-1]} dBm at {EIRP_RANGE_DBM[1]-EIRP_RANGE_DBM[0]:.1f} dB steps\n")

    for name, freq in BANDS.items():
        pl_by_eps = precompute_path_loss(dem, px, tx, freq, [EPS_LOW, EPS_HIGH])
        c_lo = coverage_curve(pl_by_eps[EPS_LOW], EIRP_RANGE_DBM)
        c_hi = coverage_curve(pl_by_eps[EPS_HIGH], EIRP_RANGE_DBM)
        delta = c_hi - c_lo
        max_abs = np.max(np.abs(delta))
        eirp_at_max = EIRP_RANGE_DBM[np.argmax(np.abs(delta))]
        print(f"{name}-band ({freq/1e9:.3f} GHz): max |delta coverage| = "
              f"{max_abs:.2f}% at EIRP = {eirp_at_max:.1f} dBm")


if __name__ == "__main__":
    main()

"""
RECHECK of dielectric_by_band.py: the original 2 dB EIRP resolution may have
undersampled the true sensitivity peak differently at S vs Ka (interference
fringes can have different spacing in EIRP-space at different wavelengths),
which could make "S > Ka" a resolution artifact rather than a real result.

This script re-runs the SAME comparison (eps'=2.5 vs 8.0, S vs Ka) at a much
finer EIRP resolution (0.2 dB instead of 2 dB) over the same range, and
reports both the coarse and fine max|delta| side by side so the original
result can be checked directly against a properly resolved one.

Path loss is precomputed once per band/eps (independent of EIRP), so
increasing EIRP resolution is cheap -- it does not require recomputing
diffraction or two-ray path loss, only re-scanning the same arrays at finer
EIRP steps.

Run from the project root:  python dielectric_by_band_recheck.py
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

EIRP_COARSE = np.arange(-30, 61, 2.0)   # the original resolution
EIRP_FINE = np.arange(-30, 61, 0.2)     # 10x finer, same range


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def precompute_path_loss(dem, px, tx, freq_hz, eps_values):
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    ii, jj = np.mgrid[0:ny, 0:nx]
    dh = np.hypot(ii - tx[0], jj - tx[1]) * px

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
    n_valid = int(np.sum(valid)) + 1
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
    print(f"Coarse: {len(EIRP_COARSE)} points @ 2.0 dB step | Fine: {len(EIRP_FINE)} points @ 0.2 dB step\n")

    results = {}
    for name, freq in BANDS.items():
        print(f"--- {name}-band ({freq/1e9:.3f} GHz) ---")
        pl_by_eps = precompute_path_loss(dem, px, tx, freq, [EPS_LOW, EPS_HIGH])

        c_lo_coarse = coverage_curve(pl_by_eps[EPS_LOW], EIRP_COARSE)
        c_hi_coarse = coverage_curve(pl_by_eps[EPS_HIGH], EIRP_COARSE)
        delta_coarse = c_hi_coarse - c_lo_coarse
        max_coarse = np.max(np.abs(delta_coarse))
        eirp_coarse = EIRP_COARSE[np.argmax(np.abs(delta_coarse))]

        c_lo_fine = coverage_curve(pl_by_eps[EPS_LOW], EIRP_FINE)
        c_hi_fine = coverage_curve(pl_by_eps[EPS_HIGH], EIRP_FINE)
        delta_fine = c_hi_fine - c_lo_fine
        max_fine = np.max(np.abs(delta_fine))
        eirp_fine = EIRP_FINE[np.argmax(np.abs(delta_fine))]

        results[name] = (max_coarse, max_fine)
        print(f"  coarse (2.0 dB step): max |delta| = {max_coarse:.3f}% at EIRP={eirp_coarse:.1f} dBm")
        print(f"  fine   (0.2 dB step): max |delta| = {max_fine:.3f}% at EIRP={eirp_fine:.1f} dBm")
        print(f"  undersampling ratio (fine/coarse): {max_fine/max(max_coarse,1e-9):.2f}x\n")

    print("=" * 60)
    print("RECHECKED PREDICTION TEST (fine resolution, matched between bands):")
    print(f"  S-band  max |delta| -- coarse: {results['S'][0]:.3f}%   fine: {results['S'][1]:.3f}%")
    print(f"  Ka-band max |delta| -- coarse: {results['Ka'][0]:.3f}%   fine: {results['Ka'][1]:.3f}%")
    if results["Ka"][1] > results["S"][1]:
        print("  -> At matched fine resolution: Ka IS larger than S. The original")
        print("     coarse-resolution comparison was misleading (resolution artifact).")
    else:
        print("  -> At matched fine resolution: S remains larger than Ka. The original")
        print("     finding holds up -- not a resolution artifact.")


if __name__ == "__main__":
    main()

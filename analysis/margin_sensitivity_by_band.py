"""
Follow-up to dielectric_by_band.py's 'not confirmed' coverage-percentage
result: tests whether the underlying PER-PIXEL MARGIN sensitivity to
permittivity (eps'=2.5 vs 8.0), at LOS pixels only, actually grows with
frequency (S -> Ka) even though the coverage-PERCENTAGE effect did not.

Rationale: the LOS mask is frequency-independent (pure geometry), but
overall coverage is much lower at Ka, so the pixels near the 0 dB coverage
threshold at Ka may be dominated by NLOS/diffraction pixels (which cannot
respond to permittivity at all). This script sidesteps that confound by
looking at margin change directly on the LOS population, not at whether
coverage flips.

Run from the project root:  python margin_sensitivity_by_band.py
"""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx
from lunarcomms.propagation import two_ray, friis

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
H_TX, H_RX = 30.0, 2.0
EPS_LOW, EPS_HIGH = 2.5, 8.0
BANDS = {"S": 2.5e9, "Ka": 27.0e9}


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    los_no_tx = los.copy()
    los_no_tx[tx] = False

    ii, jj = np.mgrid[0:ny, 0:nx]
    dh = np.hypot(ii - tx[0], jj - tx[1]) * px
    dh_los = dh[los_no_tx]

    print(f"DEM {dem.shape}, TX {tx}, n LOS pixels = {los_no_tx.sum()}\n")
    print(f"{'Band':6s} {'mean|delta PL|':>15s} {'max|delta PL|':>15s} {'median dist(m)':>15s}")
    print("-" * 55)

    rho_lo, rho_hi = rho_for_eps(EPS_LOW), rho_for_eps(EPS_HIGH)
    for name, freq in BANDS.items():
        pl_lo = two_ray.path_loss_db(dh_los, H_TX, H_RX, freq, rho_lo)
        pl_hi = two_ray.path_loss_db(dh_los, H_TX, H_RX, freq, rho_hi)
        delta = pl_hi - pl_lo
        print(f"{name:6s} {np.mean(np.abs(delta)):>14.4f} dB {np.max(np.abs(delta)):>13.4f} dB "
              f"{np.median(dh_los):>14.1f}")

    print()
    print("If mean/max |delta PL| is LARGER at Ka than S here, the underlying")
    print("per-pixel dielectric sensitivity DOES grow with frequency, as")
    print("predicted -- even though the coverage-PERCENTAGE test did not show")
    print("it, because Ka's near-threshold pixels are mostly NLOS/diffraction-")
    print("dominated (eps-blind) rather than LOS/two-ray (eps-sensitive).")


if __name__ == "__main__":
    main()

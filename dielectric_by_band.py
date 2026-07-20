"""
Tests the pre-registered prediction (progress report Section 6.5): dielectric
influence on coverage is small at S-band and should GROW at Ka-band.

Runs the SAME stress-test methodology used for S-band (forced eps'=2.5 vs
eps'=8.0, swept across a range of EIRP) at BOTH S-band and Ka-band, so the
two can be directly compared: does the maximum |delta coverage| get larger
at Ka, as predicted?

Run from the project root:  python dielectric_by_band.py
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
EIRP_RANGE_DBM = np.arange(-30, 61, 2)  # wide sweep to find each band's sensitive zone


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
    print(f"Testing prediction: dielectric effect (eps'={EPS_LOW} vs {EPS_HIGH}) "
          f"should be larger at Ka than at S.\n")

    results = {}
    for name, freq in BANDS.items():
        print(f"--- {name}-band ({freq/1e9:.3f} GHz) ---")
        pl_by_eps = precompute_path_loss(dem, px, tx, freq, [EPS_LOW, EPS_HIGH])
        c_lo = coverage_curve(pl_by_eps[EPS_LOW], EIRP_RANGE_DBM)
        c_hi = coverage_curve(pl_by_eps[EPS_HIGH], EIRP_RANGE_DBM)
        delta = c_hi - c_lo
        max_abs = np.max(np.abs(delta))
        max_eirp = EIRP_RANGE_DBM[np.argmax(np.abs(delta))]
        results[name] = max_abs
        print(f"  max |delta coverage|: {max_abs:.3f}% at EIRP={max_eirp} dBm")
        print(f"  mean |delta coverage| across sweep: {np.mean(np.abs(delta)):.3f}%\n")

    print("=" * 50)
    print("PREDICTION TEST:")
    print(f"  S-band max |delta|:  {results['S']:.3f}%")
    print(f"  Ka-band max |delta|: {results['Ka']:.3f}%")
    if results["Ka"] > results["S"]:
        print("  -> CONFIRMED: dielectric sensitivity is larger at Ka-band.")
    else:
        print("  -> NOT CONFIRMED on this subset: Ka-band sensitivity is not "
              "larger than S-band. Worth reporting as-is (a real result either way).")


if __name__ == "__main__":
    main()

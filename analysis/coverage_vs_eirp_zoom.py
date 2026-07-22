

"""
Zoomed-in coverage vs. EIRP (-30 to +10 dBm), to visually confirm the
dielectric sign-flip found in the link-budget stress test (eps'=2.5 vs 7.0).

Top panel: coverage % curves for eps'=2.5 and eps'=7.0, overlapping almost
           everywhere except where they visibly separate.
Bottom panel: the DIRECT DIFFERENCE (eps=7.0 minus eps=2.5) -- this makes the
              small, sign-flipping effect visible even where the top panel's
              curves look identical to the eye.

Reuses the same precompute-once-then-sweep approach as
coverage_vs_eirp_terrain.py (path loss computed once per eps, independent of
EIRP; only the final threshold count varies with EIRP).

Produces coverage_vs_eirp_zoom.png. Run from the project root:
    python coverage_vs_eirp_zoom.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

# ---- config -------------------------------------------------------------
DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
EPS_LOW, EPS_HIGH = 2.5, 7.0          # the two extremes being compared
EIRP_RANGE_DBM = np.arange(-30, 11, 1)  # fine 1 dB steps, zoomed window
# -------------------------------------------------------------------------


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def precompute_path_loss(dem, px, tx, eps_values):
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    ii, jj = np.mgrid[0:ny, 0:nx]
    dh = np.hypot(ii - tx[0], jj - tx[1]) * px

    nlos_pl = np.full((ny, nx), np.nan)
    nlos_idx = np.argwhere(~los)
    print(f"  computing diffraction for {len(nlos_idx)} NLOS pixels...")
    for (i, j) in nlos_idx:
        if (i, j) == tx:
            continue
        rx_elev = dem[i, j] + H_RX
        d3d = np.hypot(dh[i, j], rx_elev - tx_elev)
        pl = float(friis.fspl_db(d3d, FREQ_HZ))
        h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
        pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, FREQ_HZ))
        nlos_pl[i, j] = pl

    pl_by_eps = {}
    los_no_tx = los.copy()
    los_no_tx[tx] = False
    for eps in eps_values:
        rho = rho_for_eps(eps)
        pl = np.full((ny, nx), np.nan)
        pl[los_no_tx] = two_ray.path_loss_db(dh[los_no_tx], H_TX, H_RX, FREQ_HZ, rho)
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

    pl_by_eps = precompute_path_loss(dem, px, tx, [EPS_LOW, EPS_HIGH])
    c_lo = coverage_curve(pl_by_eps[EPS_LOW], EIRP_RANGE_DBM)
    c_hi = coverage_curve(pl_by_eps[EPS_HIGH], EIRP_RANGE_DBM)
    delta = c_hi - c_lo

    print(f"\nmax |delta|: {np.max(np.abs(delta)):.3f}% at EIRP={EIRP_RANGE_DBM[np.argmax(np.abs(delta))]} dBm")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})

    ax1.plot(EIRP_RANGE_DBM, c_lo, color="#2E7D32", lw=2, label="eps'=2.5 (regolith)")
    ax1.plot(EIRP_RANGE_DBM, c_hi, color="#C62828", lw=2, label="eps'=7.0 (basalt/rock)")
    ax1.set_ylabel("Coverage (%)")
    ax1.set_title("Zoomed coverage vs. EIRP: does dielectric ever flip coverage?")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    ax2.axhline(0, color="gray", lw=1)
    ax2.plot(EIRP_RANGE_DBM, delta, color="black", lw=1.5)
    ax2.fill_between(EIRP_RANGE_DBM, delta, 0, where=(delta > 0),
                     color="#C62828", alpha=0.3, label="rock helps")
    ax2.fill_between(EIRP_RANGE_DBM, delta, 0, where=(delta < 0),
                     color="#2E7D32", alpha=0.3, label="rock hurts")
    ax2.set_ylabel("\u0394 coverage (%)\n(eps=7.0 minus eps=2.5)")
    ax2.set_xlabel("EIRP (dBm)")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig("coverage_vs_eirp_zoom.png", dpi=130, bbox_inches="tight")
    print("wrote coverage_vs_eirp_zoom.png")


if __name__ == "__main__":
    main()

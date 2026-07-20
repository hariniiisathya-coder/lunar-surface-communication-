"""
Coverage % vs EIRP (0-80 dBm), WITH terrain (LOS -> two-ray, NLOS -> FSPL +
Deygout diffraction), for eps' = 2.5 (regolith), 3.2 (typical mare), 7.0
(basalt / crater-wall rock). Friis-only (no terrain, no multipath) shown for
reference. EVA suit (23 dBm) and BTS (53 dBm) EIRP marked as vertical lines.

Optimised: path loss is computed ONCE per pixel per eps (independent of
EIRP), then the EIRP sweep is a cheap vectorised threshold count -- not a
full pipeline recomputation at every EIRP value.

Produces coverage_vs_eirp_terrain.png. Run from the project root:
    python coverage_vs_eirp_terrain.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

# ---- config -----------------------------------------------------------
DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
EPS_VALUES = [2.5, 3.2, 7.0]
EIRP_RANGE_DBM = np.arange(0, 81, 2)
EVA_EIRP, BTS_EIRP = 23.0, 53.0
# -------------------------------------------------------------------------


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def precompute_path_loss(dem, px, tx, eps_values):
    """Compute full-DEM path-loss arrays once per eps (LOS via two-ray, NLOS
    via FSPL+Deygout -- diffraction loss is eps-independent, computed once).
    Returns (dict eps->path_loss array, los mask)."""
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX

    ii, jj = np.mgrid[0:ny, 0:nx]
    dh = np.hypot(ii - tx[0], jj - tx[1]) * px

    # NLOS path loss (FSPL + Deygout): identical for every eps, compute once
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
        print(f"  eps={eps} two-ray LOS path loss computed")

    # Friis-only (no terrain, no multipath) reference: FSPL at 3-D distance
    rx_elev_all = dem + H_RX
    d3d_all = np.hypot(dh, rx_elev_all - tx_elev)
    friis_pl = friis.fspl_db(d3d_all, FREQ_HZ)
    friis_pl[tx] = np.nan

    return pl_by_eps, friis_pl, los


def coverage_curve(pl, eirp_range, tx):
    """Vectorised coverage % for a sweep of EIRP values, given a precomputed
    path-loss array. O(1) per EIRP value -- no pipeline recomputation."""
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
    print(f"DEM {dem.shape}, px={px} m, TX {tx}, elev {dem[tx]:.1f} m")

    pl_by_eps, friis_pl, los = precompute_path_loss(dem, px, tx, EPS_VALUES)
    print(f"  LOS fraction: {los.mean():.1%}  (NLOS/terrain-shadowed: {1-los.mean():.1%})\n")

    friis_curve = coverage_curve(friis_pl, EIRP_RANGE_DBM, tx)
    tworay_curves = {eps: coverage_curve(pl_by_eps[eps], EIRP_RANGE_DBM, tx)
                      for eps in EPS_VALUES}

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(EIRP_RANGE_DBM, friis_curve, "k--", lw=2, label="Friis (free space, no terrain)")

    colors = {2.5: "#2E7D32", 3.2: "#F9A825", 7.0: "#C62828"}
    labels = {2.5: "eps'=2.5 (regolith)", 3.2: "eps'=3.2 (typical mare)",
              7.0: "eps'=7.0 (basalt / crater-wall rock)"}
    for eps in EPS_VALUES:
        ax.plot(EIRP_RANGE_DBM, tworay_curves[eps], color=colors[eps], lw=2,
                label=f"Terrain-aware (two-ray+Deygout), {labels[eps]}")

    ax.axvline(EVA_EIRP, color="gray", linestyle=":", lw=1.5)
    ax.text(EVA_EIRP + 1, 5, f"EVA suit\n{EVA_EIRP:.0f} dBm", fontsize=9, color="gray")
    ax.axvline(BTS_EIRP, color="gray", linestyle=":", lw=1.5)
    ax.text(BTS_EIRP + 1, 5, f"BTS\n{BTS_EIRP:.0f} dBm", fontsize=9, color="gray")

    ax.set_xlabel("EIRP (dBm)")
    ax.set_ylabel("Coverage (%)")
    ax.set_title("Coverage vs. EIRP (terrain-aware) \u2014 Site01, 2 km subset, S-band")
    ax.set_xlim(0, 80)
    ax.set_ylim(0, 102)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.savefig("coverage_vs_eirp_terrain.png", dpi=130, bbox_inches="tight")
    print("wrote coverage_vs_eirp_terrain.png")


if __name__ == "__main__":
    main()

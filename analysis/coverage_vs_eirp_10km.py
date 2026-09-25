"""Coverage vs EIRP over the 10 km Site01 tile, TERRAIN-AWARE (LOS mask +
two-ray + Deygout), for three regolith permittivities, plus a no-terrain Friis
ceiling. Path loss per pixel is computed once per permittivity; the EIRP sweep is
a threshold on the precomputed loss. Writes <out_dir>/eirp_curves.json and a
quick-look plot. Usage: python analysis/coverage_vs_eirp_10km.py [out_dir]
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile, diffraction_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 5.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
STRIDE = 2
EPS_VALUES = [2.5, 3.2, 7.0]
EIRP_RANGE = np.arange(0, 81, 2)
EVA_EIRP, BTS_EIRP = 23.0, 53.0


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def loss_maps(dem, px, tx, rho):
    """Return (pl_terrain[], pl_friis[]) flat arrays over sampled valid pixels."""
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    pl_t, pl_f = [], []
    for i in range(0, ny, STRIDE):
        for j in range(0, nx, STRIDE):
            if np.isnan(dem[i, j]) or (i, j) == tx:
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            d3d = np.hypot(dh, rx_elev - tx_elev)
            f = float(friis.fspl_db(d3d, FREQ_HZ))
            if los[i, j]:
                t = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ_HZ, rho))
            else:
                h, dist = diffraction_profile(dem, tx[0], tx[1], i, j, px)
                t = f + float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, FREQ_HZ))
            pl_t.append(t)
            pl_f.append(f)
    return np.array(pl_t), np.array(pl_f)


def cov(pl, eirp):
    return 100.0 * np.mean((eirp + GRX - pl) > SENS)


def main():
    dem, transform, _ = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, TX {tx}, elev {dem[tx]:.1f} m", flush=True)

    curves = {}
    pl_f_ref = None
    for eps in EPS_VALUES:
        pl_t, pl_f = loss_maps(dem, px, tx, rho_for_eps(eps))
        curves[eps] = np.array([cov(pl_t, e) for e in EIRP_RANGE])
        pl_f_ref = pl_f
        i_bts = int(np.argmin(np.abs(EIRP_RANGE - BTS_EIRP)))
        print(f"  eps={eps}: plateau {curves[eps][-1]:.1f}% at 80 dBm, "
              f"{curves[eps][i_bts]:.1f}% near BTS", flush=True)
    friis_curve = np.array([cov(pl_f_ref, e) for e in EIRP_RANGE])
    # curves for analysis/paper_figures.py (fig "eirp"); the plot below is a quick look
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    json.dump({"eirp_dbm": EIRP_RANGE.tolist(), "friis": friis_curve.tolist(),
               "terrain": {str(k): v.tolist() for k, v in curves.items()}},
              open(os.path.join(out_dir, "eirp_curves.json"), "w"))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(EIRP_RANGE, friis_curve, "k--", lw=2, label="Friis (free space, no terrain)")
    colors = {2.5: "#2E7D32", 3.2: "#F9A825", 7.0: "#C62828"}
    labels = {2.5: "eps'=2.5 (regolith)", 3.2: "eps'=3.2 (typical mare)",
              7.0: "eps'=7.0 (basalt / crater-wall rock)"}
    for eps in EPS_VALUES:
        ax.plot(EIRP_RANGE, curves[eps], color=colors[eps], lw=2,
                label=f"Terrain-aware, {labels[eps]}")
    ax.axvline(EVA_EIRP, color="gray", ls=":", lw=1.5)
    ax.text(EVA_EIRP + 1, 40, f"EVA suit\n{EVA_EIRP:.0f} dBm", fontsize=9, color="gray")
    ax.axvline(BTS_EIRP, color="gray", ls=":", lw=1.5)
    ax.text(BTS_EIRP + 1, 40, f"BTS\n{BTS_EIRP:.0f} dBm", fontsize=9, color="gray")
    ax.set_xlabel("EIRP (dBm)"); ax.set_ylabel("Coverage (%)")
    ax.set_title("Coverage vs. EIRP — Site01, 10 km tile, S-band (2.5 GHz)")
    ax.set_xlim(0, 80); ax.set_ylim(0, 102); ax.grid(alpha=0.3)
    ax.legend(loc="center right", fontsize=9)
    plt.tight_layout()
    out = os.path.join(out_dir, "coverage_vs_eirp_quicklook.png")
    plt.savefig(out, dpi=130, bbox_inches="tight")
    print(f"\nwrote {out}", flush=True)


if __name__ == "__main__":
    main()

"""
Coverage % vs EIRP, for Friis and two-ray, at three permittivities
(eps' = 2.5 regolith, 3.2 typical mare, 7.0 basalt/crater-wall rock),
with EVA-suit (23 dBm) and BTS (53 dBm) EIRP marked as reference lines.

Produces coverage_vs_eirp.png. Run from the project root:
    python coverage_vs_eirp.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcomms.io.pgda import load_dem
from lunarcomms.propagation import two_ray, friis

# ---- config ---------------------------------------------------------------
DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0          # ~2 km x 2 km subset
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
GRX, SENS = 2.0, -106.0
EPS_VALUES = [2.5, 3.2, 7.0]           # regolith, typical mare, basalt/rock
EIRP_RANGE_DBM = np.arange(0, 81, 2)   # 0 to 80 dBm, 2 dB steps
EVA_EIRP = 23.0
BTS_EIRP = 53.0
# -----------------------------------------------------------------------------


def rho_for_eps(eps):
    """Density that yields real permittivity eps via eps' = 1.919**rho."""
    return np.log(eps) / np.log(1.919)


def coverage_pct(dem, px, tx, eirp, rho, model):
    """Coverage % for a single EIRP / model / permittivity combination."""
    ny, nx = dem.shape
    covered = total = 0
    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx:
                covered += 1
                total += 1
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            if model == "friis":
                pl = float(friis.fspl_db(dh, FREQ_HZ))
            else:  # tworay
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ_HZ, rho))
            prx = friis.received_power_dbm(eirp, pl, GRX)
            margin = friis.link_margin_db(prx, SENS)
            total += 1
            if margin > 0:
                covered += 1
    return 100 * covered / total


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, px={px} m, TX {tx}, elev {dem[tx]:.1f} m")
    print(f"EIRP sweep: {EIRP_RANGE_DBM[0]}-{EIRP_RANGE_DBM[-1]} dBm, "
          f"{len(EIRP_RANGE_DBM)} points x {len(EPS_VALUES)} eps x 2 models "
          f"= {len(EIRP_RANGE_DBM)*len(EPS_VALUES)*2} coverage runs\n")

    # Friis doesn't depend on eps, so compute it once
    friis_curve = np.array([coverage_pct(dem, px, tx, e, None, "friis")
                             for e in EIRP_RANGE_DBM])

    tworay_curves = {}
    for eps in EPS_VALUES:
        rho = rho_for_eps(eps)
        tworay_curves[eps] = np.array([
            coverage_pct(dem, px, tx, e, rho, "tworay") for e in EIRP_RANGE_DBM
        ])
        print(f"  eps={eps} done")

    # ---- plot ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(EIRP_RANGE_DBM, friis_curve, "k--", lw=2, label="Friis (free space)")

    colors = {2.5: "#2E7D32", 3.2: "#F9A825", 7.0: "#C62828"}
    labels = {2.5: "eps'=2.5 (regolith)", 3.2: "eps'=3.2 (typical mare)",
              7.0: "eps'=7.0 (basalt / crater-wall rock)"}
    for eps in EPS_VALUES:
        ax.plot(EIRP_RANGE_DBM, tworay_curves[eps], color=colors[eps], lw=2,
                label=f"Two-ray, {labels[eps]}")

    ax.axvline(EVA_EIRP, color="gray", linestyle=":", lw=1.5)
    ax.text(EVA_EIRP + 1, 5, f"EVA suit\n{EVA_EIRP:.0f} dBm", fontsize=9, color="gray")
    ax.axvline(BTS_EIRP, color="gray", linestyle=":", lw=1.5)
    ax.text(BTS_EIRP + 1, 5, f"BTS\n{BTS_EIRP:.0f} dBm", fontsize=9, color="gray")

    ax.set_xlabel("EIRP (dBm)")
    ax.set_ylabel("Coverage (%)")
    ax.set_title("Coverage vs. EIRP \u2014 Site01, 2 km subset, S-band (2.5 GHz)")
    ax.set_xlim(0, 80)
    ax.set_ylim(0, 102)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.savefig("coverage_vs_eirp.png", dpi=130, bbox_inches="tight")
    print("\nwrote coverage_vs_eirp.png")


if __name__ == "__main__":
    main()

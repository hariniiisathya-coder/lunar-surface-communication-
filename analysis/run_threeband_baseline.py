"""
Three-band terrain-aware coverage comparison: UHF (0.442 GHz), S-band
(2.5 GHz), Ka-band (27 GHz) -- WITH a coverage-vs-frequency figure.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction
from lunarcomms.regolith import dielectric as di

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS, RHO = 53.0, 2.0, -106.0, 1.50

BANDS = {"UHF": 0.442e9, "S": 2.5e9, "Ka": 27.0e9}


def run_band(dem, px, tx, freq_hz):
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX

    covered_friis = covered_terrain = total = 0
    clamp_hits = nlos_count = 0

    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx:
                covered_friis += 1
                covered_terrain += 1
                total += 1
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            d3d = np.hypot(dh, rx_elev - tx_elev)

            pl_f = float(friis.fspl_db(d3d, freq_hz))
            m_f = friis.link_margin_db(friis.received_power_dbm(EIRP, pl_f, GRX), SENS)

            if los[i, j]:
                pl_t = float(two_ray.path_loss_db(dh, H_TX, H_RX, freq_hz, RHO))
            else:
                nlos_count += 1
                pl_t = pl_f
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                pl_t += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, freq_hz))
                td_raw = float(di.loss_tangent_ab(-3.79, 0.069, freq_hz / 1e9, clamp=False))
                if td_raw > di.TAN_DELTA_CEILING:
                    clamp_hits += 1

            m_t = friis.link_margin_db(friis.received_power_dbm(EIRP, pl_t, GRX), SENS)

            total += 1
            if m_f > 0:
                covered_friis += 1
            if m_t > 0:
                covered_terrain += 1

    friis_pct = 100 * covered_friis / total
    terrain_pct = 100 * covered_terrain / total
    clamp_frac = 100 * clamp_hits / nlos_count if nlos_count else 0.0
    return friis_pct, terrain_pct, clamp_frac


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, TX {tx}, elev {dem[tx]:.1f} m\n")

    results = {}
    print(f"{'Band':6s} {'Freq (GHz)':>10s} {'Breakpoint(m)':>14s} "
          f"{'Friis %':>9s} {'Terrain %':>10s} {'Penalty %':>10s} {'UHF-clamp hit %':>16s}")
    print("-" * 82)
    for name, f in BANDS.items():
        bp = two_ray.breakpoint_distance(H_TX, H_RX, f)
        friis_pct, terrain_pct, clamp_frac = run_band(dem, px, tx, f)
        penalty = friis_pct - terrain_pct
        results[name] = (f, friis_pct, terrain_pct, penalty)
        print(f"{name:6s} {f/1e9:>10.3f} {bp:>14.1f} {friis_pct:>8.1f}% "
              f"{terrain_pct:>9.1f}% {penalty:>9.1f}% {clamp_frac:>15.1f}%")

    order = ["UHF", "S", "Ka"]
    freqs_ghz = [results[b][0] / 1e9 for b in order]
    friis_vals = [results[b][1] for b in order]
    terrain_vals = [results[b][2] for b in order]
    penalty_vals = [results[b][3] for b in order]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(freqs_ghz, friis_vals, "k--", marker="o", label="Friis (no terrain)")
    ax1.plot(freqs_ghz, terrain_vals, color="#C62828", marker="o", lw=2,
              label="Terrain-aware (two-ray+Deygout)")
    ax1.set_xscale("log")
    ax1.set_xticks(freqs_ghz)
    ax1.set_xticklabels([f"{b}\n{f:.3g} GHz" for b, f in zip(order, freqs_ghz)])
    ax1.set_ylabel("Coverage (%)")
    ax1.set_ylim(0, 105)
    ax1.set_title("Coverage vs. band")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.plot(freqs_ghz, penalty_vals, color="#C62828", marker="o", lw=2)
    ax2.set_xscale("log")
    ax2.set_xticks(freqs_ghz)
    ax2.set_xticklabels([f"{b}\n{f:.3g} GHz" for b, f in zip(order, freqs_ghz)])
    ax2.set_ylabel("Terrain penalty (%) = Friis % \u2212 Terrain-aware %")
    ax2.set_title("Terrain-blockage penalty vs. band\n(the predicted collapse)")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig("threeband_coverage.png", dpi=130, bbox_inches="tight")
    print("\nwrote threeband_coverage.png")


if __name__ == "__main__":
    main()

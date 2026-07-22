"""
Per-band coverage / throughput map comparison over a real DEM.

Runs the full pipeline physics (LOS -> two-ray + regolith Fresnel; NLOS ->
FSPL + Deygout diffraction) at UHF / S / Ka on the SAME terrain and lays the
throughput maps side by side, so the terrain-blockage penalty growing with
frequency is visible spatially, not just as a coverage percentage.

The line-of-sight mask is geometry only, so it is computed ONCE and reused
across bands; only the path loss is band-dependent (diffraction loss ~ sqrt(f),
which is what shrinks Ka coverage).

Per-pixel throughput is a Shannon estimate capped at a 256QAM ceiling
(7.4 b/s/Hz), i.e. an achievable-rate planning map; the companion PUSCH BLER
sim (matlab/run_pusch_bler.m) validates the SNR->rate relationship at one MCS
(16QAM R=0.48 closes ~28 Mbps near 8-9 dB SNR).

Link budget is held fixed across bands (same EIRP and antenna gains) to isolate
the propagation/terrain effect -- the honest comparison, since a fixed-aperture
antenna would instead GAIN ~f^2 with frequency (paper Sec. 2.5), a separate
axis. Run from the project root:

    python analysis/band_comparison_maps.py --dem <tif> --clip-km 1.0 --stride 3
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource

from lunarcomms.geometry.horizon import extract_profile, los_mask_from_tx
from lunarcomms.io.pgda import load_dem
from lunarcomms.propagation import diffraction, friis, two_ray

BANDS = {"UHF (0.44 GHz)": 0.442e9, "S (2.5 GHz)": 2.5e9, "Ka (27 GHz)": 27.0e9}

# Fixed link budget across bands (BS downlink).
EIRP_DBM, GRX_DBI, NF_DB, B_HZ, RHO = 53.0, 2.0, 5.0, 20e6, 1.50
H_TX, H_RX = 30.0, 2.0
SE_MAX = 7.4                      # 256QAM ceiling, b/s/Hz
SNR_MIN_DB = 0.0                 # below this a pixel is "uncovered"
N0_DBM = -174 + 10 * np.log10(B_HZ) + NF_DB


def snr_map_for_band(dem, px, tx_rc, los, freq_hz, stride):
    """Per-pixel downlink SNR (dB) at one band, given the precomputed LOS mask."""
    ny, nx = dem.shape
    tx_elev = dem[tx_rc] + H_TX
    snr = np.full((ny, nx), np.nan)
    for i in range(0, ny, stride):
        for j in range(0, nx, stride):
            if np.isnan(dem[i, j]):
                continue
            if (i, j) == tuple(tx_rc):
                pl = 0.0
            else:
                dh = float(np.hypot(i - tx_rc[0], j - tx_rc[1]) * px)
                rx_elev = dem[i, j] + H_RX
                d3d = float(np.hypot(dh, rx_elev - tx_elev))
                if los[i, j]:
                    pl = float(two_ray.path_loss_db(dh, H_TX, H_RX,
                                                    freq_hz, RHO))
                else:
                    pl = float(friis.fspl_db(d3d, freq_hz))
                    h, dist = extract_profile(dem, tx_rc[0], tx_rc[1],
                                              i, j, px)
                    pl += float(diffraction.deygout_loss_db(
                        h, dist, H_TX, H_RX, freq_hz))
            prx = EIRP_DBM + GRX_DBI - pl
            snr[i:i + stride, j:j + stride] = prx - N0_DBM
    snr[np.isnan(dem)] = np.nan
    return snr


def throughput_map(snr_db):
    """Shannon achievable rate (Mbps), 256QAM-capped, 0 below SNR_MIN_DB."""
    se = np.minimum(np.log2(1.0 + 10.0 ** (snr_db / 10.0)), SE_MAX)
    tput = B_HZ * se / 1e6
    tput[snr_db < SNR_MIN_DB] = 0.0
    return tput


def main():
    ap = argparse.ArgumentParser(description="Per-band coverage/throughput maps.")
    ap.add_argument("--dem", default="data/dem/Site04/Site04_final_adj_5mpp_surf.tif")
    ap.add_argument("--clip-km", type=float, default=1.0)
    ap.add_argument("--tx-frac", type=float, nargs=2, default=(0.5, 0.5))
    ap.add_argument("--stride", type=int, default=3)
    ap.add_argument("--out", default="figures/band_comparison_maps.png")
    args = ap.parse_args()

    dem, transform, _ = load_dem(args.dem, clip_extent_km=args.clip_km)
    px = abs(transform.a)
    ny, nx = dem.shape
    tx_rc = (int(round(args.tx_frac[0] * (ny - 1))),
             int(round(args.tx_frac[1] * (nx - 1))))
    print(f"DEM {ny}x{nx} @ {px:.0f} m, mast {tx_rc} (elev {dem[tx_rc]:.0f} m)")

    # LOS mask: geometry only -> compute once, reuse for every band.
    los = los_mask_from_tx(dem, px, tx_rc[0], tx_rc[1], H_TX, H_RX)
    shadowed = 100.0 * (1.0 - los.mean())
    print(f"terrain-shadowed pixels: {shadowed:.1f}%")

    tputs, stats = {}, {}
    for name, f in BANDS.items():
        snr = snr_map_for_band(dem, px, tx_rc, los, f, args.stride)
        tp = throughput_map(snr)
        tputs[name] = tp
        computed = np.isfinite(snr)
        cov = 100.0 * np.mean(snr[computed] >= SNR_MIN_DB)
        med = float(np.median(tp[computed][tp[computed] > 0])) if np.any(
            tp[computed] > 0) else 0.0
        stats[name] = (cov, med)
        print(f"  {name}: coverage {cov:.1f}%, median served throughput "
              f"{med:.0f} Mbps")

    # ---- figure: hillshade + throughput per band, shared colour scale ----
    extent = [0, nx * px / 1e3, ny * px / 1e3, 0]
    ls = LightSource(azdeg=315, altdeg=35)
    shade = ls.hillshade(np.where(np.isnan(dem), np.nanmin(dem), dem),
                         vert_exag=2, dx=px, dy=px)
    vmax = max(np.nanmax(tp) for tp in tputs.values())

    fig, axes = plt.subplots(1, len(BANDS), figsize=(5.0 * len(BANDS), 5.2))
    im = None
    for ax, (name, tp) in zip(axes, tputs.items()):
        ax.imshow(shade, cmap="gray", extent=extent, interpolation="bilinear")
        masked = np.ma.masked_less_equal(tp, 0.0)
        im = ax.imshow(masked, cmap="viridis", extent=extent, alpha=0.72,
                       vmin=0, vmax=vmax, interpolation="nearest")
        ax.plot(tx_rc[1] * px / 1e3, tx_rc[0] * px / 1e3, "^", color="red",
                ms=9, mec="white")
        cov, med = stats[name]
        ax.set_title(f"{name}\ncoverage {cov:.0f}%   median {med:.0f} Mbps",
                     fontsize=10)
        ax.set_xlabel("east (km)")
    axes[0].set_ylabel("south (km)")
    cb = fig.colorbar(im, ax=axes, shrink=0.82, pad=0.02)
    cb.set_label("achievable throughput (Mbps, 20 MHz, 256QAM cap)")
    fig.suptitle(f"Per-band coverage over real terrain (Site04, "
                 f"{shadowed:.0f}% shadowed) — fixed link budget",
                 fontsize=12)
    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()

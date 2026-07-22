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

# Link budget held fixed across bands (only propagation differs).
NF_DB, B_HZ, RHO = 5.0, 20e6, 1.50
H_TX, H_RX = 30.0, 2.0
SE_MAX = 7.4                      # 256QAM ceiling, b/s/Hz (Shannon fallback)
SNR_MIN_DB = 0.0                 # below this a pixel is "uncovered"
N0_DBM = -174 + 10 * np.log10(B_HZ) + NF_DB


def snr_map_for_band(dem, px, tx_rc, los, freq_hz, stride, eirp_dbm, grx_dbi):
    """Per-pixel SNR (dB) at one band, given the precomputed LOS mask."""
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
                    # Envelope (dual-slope), not the exact coherent sum: the
                    # two-ray nulls are fast fading that aliases into moire on
                    # a pixel-sampled map. The exact oscillation lives in the
                    # tap/trajectory export where a rover resolves it.
                    pl = float(two_ray.path_loss_envelope_db(
                        dh, H_TX, H_RX, freq_hz))
                else:
                    pl = float(friis.fspl_db(d3d, freq_hz))
                    h, dist = extract_profile(dem, tx_rc[0], tx_rc[1],
                                              i, j, px)
                    pl += float(diffraction.deygout_loss_db(
                        h, dist, H_TX, H_RX, freq_hz))
            prx = eirp_dbm + grx_dbi - pl
            snr[i:i + stride, j:j + stride] = prx - N0_DBM
    snr[np.isnan(dem)] = np.nan
    return snr


def throughput_map(snr_db, amc=None):
    """Per-pixel achievable throughput (Mbps).

    amc = (snr_grid, tput_grid) from the MEASURED PUSCH link-adaptation curve
    (matlab/run_amc_curve.m): per-pixel SNR is interpolated onto it, so the
    map is MCS-accurate rather than an idealised Shannon bound. Below the
    lowest measured SNR the throughput is 0 (outage); above the top it is
    clamped to the measured peak (256QAM saturates). If amc is None, falls
    back to a 256QAM-capped Shannon estimate.
    """
    if amc is not None:
        snr_grid, tput_grid = amc
        tput = np.interp(snr_db, snr_grid, tput_grid,
                         left=0.0, right=tput_grid[-1])
        tput = np.where(np.isnan(snr_db), np.nan, tput)
        return tput
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
    ap.add_argument("--mode", choices=["bs", "ue"], default="ue",
                    help="bs: 53 dBm downlink (generous, coverage-limited); "
                    "ue: 23 dBm uplink (binding, throughput grades spatially).")
    ap.add_argument("--eirp-dbm", type=float, default=None)
    ap.add_argument("--grx-dbi", type=float, default=None)
    ap.add_argument("--amc-csv", default="matlab/amc_throughput_curve.csv",
                    help="Measured PUSCH link-adaptation curve (SNR_dB, "
                    "throughput_Mbps) from matlab/run_amc_curve.m. If absent, "
                    "falls back to a 256QAM-capped Shannon estimate.")
    ap.add_argument("--out", default="figures/band_comparison_maps.png")
    args = ap.parse_args()

    import os
    amc = None
    if os.path.exists(args.amc_csv):
        arr = np.loadtxt(args.amc_csv, delimiter=",")
        amc = (arr[:, 0], arr[:, 1])
        print(f"using measured AMC curve {args.amc_csv} "
              f"(peak {arr[:,1].max():.0f} Mbps)")
    else:
        print(f"AMC curve {args.amc_csv} not found -> Shannon fallback")

    eirp = args.eirp_dbm if args.eirp_dbm is not None else (
        53.0 if args.mode == "bs" else 23.0)
    grx = args.grx_dbi if args.grx_dbi is not None else (
        2.0 if args.mode == "bs" else 12.0)
    direction = "BS 53 dBm downlink" if args.mode == "bs" else "UE 23 dBm uplink"

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
        snr = snr_map_for_band(dem, px, tx_rc, los, f, args.stride, eirp, grx)
        tp = throughput_map(snr, amc)
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
    rate_src = "measured PUSCH AMC" if amc is not None else "256QAM Shannon"
    cb.set_label(f"achievable throughput (Mbps, {rate_src})")
    fig.suptitle(f"Per-band coverage over real terrain (Site04, "
                 f"{shadowed:.0f}% shadowed) — {direction}, {rate_src} rate",
                 fontsize=12)
    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()

"""
General coverage-map tool: any DEM GeoTIFF, one command, a link-margin map.

Drop in any LOLA/PGDA (or other) DEM tile and place a base station or a UE on
it; the tool runs the full pipeline physics per pixel (LOS -> two-ray with
regolith Fresnel; NLOS -> FSPL + Deygout diffraction over the extracted
terrain profile) and writes a margin/coverage map (PNG over a hillshade,
optional GeoTIFF).

Modes
-----
  --mode bs   downlink: the mast at --tx transmits with --eirp-dbm; the map
              shows where a receiver at --h-rx closes the link.
  --mode ue   uplink: a UE at every pixel (height --h-rx, EIRP --eirp-dbm)
              transmits toward the mast at --tx (gain --rx-gain-dbi); the map
              shows where a UE could reach the BS. Path loss is reciprocal —
              what changes is the budget, which is the point: uplink is the
              binding direction for a 23 dBm handheld against a 53 dBm BS.

Examples
--------
  # BS downlink, S-band, Site04, 1 km tile:
  python analysis/coverage_map.py --dem data/dem/Site04/Site04_final_adj_5mpp_surf.tif \
      --clip-km 1.0 --mode bs --freq-ghz 2.5 --out figures/site04_S_bs

  # UE uplink at 23 dBm (EVA-suit class), same site:
  python analysis/coverage_map.py --dem data/dem/Site04/Site04_final_adj_5mpp_surf.tif \
      --clip-km 1.0 --mode ue --eirp-dbm 23 --rx-gain-dbi 12 --sens-dbm -110 \
      --freq-ghz 2.5 --out figures/site04_S_ue

  # Put the mast somewhere else (fractions of the tile) and coarsen 2x:
  ... --tx-frac 0.3 0.7 --stride 2
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


def compute_margin_map(dem, px_m, tx_rc, h_tx, h_rx, freq_hz,
                       eirp_dbm, rx_gain_dbi, sens_dbm, rho, stride=1):
    """Per-pixel link margin (dB) with the pipeline physics.

    Reciprocal in path loss, so it serves both bs and ue modes; the caller
    chooses the budget. Returns (margin, los_mask), margin NaN outside the
    computed stride grid and on NaN DEM pixels.
    """
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px_m, tx_rc[0], tx_rc[1], h_tx, h_rx)
    tx_elev = dem[tx_rc] + h_tx
    margin = np.full((ny, nx), np.nan)

    for i in range(0, ny, stride):
        for j in range(0, nx, stride):
            if np.isnan(dem[i, j]):
                continue
            if (i, j) == tuple(tx_rc):
                m = eirp_dbm + rx_gain_dbi - sens_dbm  # on-site
            else:
                dh = float(np.hypot(i - tx_rc[0], j - tx_rc[1]) * px_m)
                rx_elev = dem[i, j] + h_rx
                d3d = float(np.hypot(dh, rx_elev - tx_elev))
                if los[i, j]:
                    pl = float(two_ray.path_loss_db(dh, h_tx, h_rx,
                                                    freq_hz, rho))
                else:
                    pl = float(friis.fspl_db(d3d, freq_hz))
                    heights, dist = extract_profile(dem, tx_rc[0], tx_rc[1],
                                                    i, j, px_m)
                    pl += float(diffraction.deygout_loss_db(
                        heights, dist, h_tx, h_rx, freq_hz))
                p_rx = friis.received_power_dbm(eirp_dbm, pl, rx_gain_dbi)
                m = friis.link_margin_db(p_rx, sens_dbm)
            # fill the whole stride block so coarse runs still render as a
            # continuous map (nearest-neighbour at stride resolution)
            margin[i:i + stride, j:j + stride] = m
    margin[np.isnan(dem)] = np.nan
    return margin, los


def plot_margin_map(dem, margin, los, px_m, tx_rc, out_png, title):
    ny, nx = dem.shape
    extent = [0, nx * px_m / 1e3, ny * px_m / 1e3, 0]  # km, row-down
    ls = LightSource(azdeg=315, altdeg=35)
    dem_f = np.where(np.isnan(dem), np.nanmin(dem), dem)
    shade = ls.hillshade(dem_f, vert_exag=2, dx=px_m, dy=px_m)

    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    ax.imshow(shade, cmap="gray", extent=extent, interpolation="bilinear")
    vmax = np.nanpercentile(np.abs(margin), 98)
    im = ax.imshow(margin, cmap="RdYlGn", extent=extent, alpha=0.62,
                   vmin=-vmax, vmax=vmax, interpolation="nearest")
    ax.contour(margin, levels=[0.0], colors="k", linewidths=1.0,
               extent=extent, origin="upper")
    ax.plot(tx_rc[1] * px_m / 1e3, tx_rc[0] * px_m / 1e3, "^",
            color="blue", ms=10, mec="white", label="mast")
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label("link margin (dB)   [black contour = 0 dB]")
    computed = np.isfinite(margin)          # stride-skipped pixels are NaN
    cov = 100.0 * np.mean(margin[computed] > 0) if computed.any() else 0.0
    shadowed = 100.0 * (1.0 - los.mean())
    ax.set_title(f"{title}\ncoverage {cov:.1f}%   terrain-shadowed pixels "
                 f"{shadowed:.1f}%", fontsize=10)
    ax.set_xlabel("east (km)")
    ax.set_ylabel("south (km)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=170)
    print(f"saved {out_png}  (coverage {cov:.1f}%, shadowed {shadowed:.1f}%)")
    return cov


def save_geotiff(margin, transform, crs, path):
    import rasterio
    with rasterio.open(
        path, "w", driver="GTiff", height=margin.shape[0],
        width=margin.shape[1], count=1, dtype="float32",
        transform=transform, crs=crs, nodata=np.nan,
    ) as dst:
        dst.write(margin.astype("float32"), 1)
    print(f"saved {path}")


def main():
    ap = argparse.ArgumentParser(
        description="Coverage map over any DEM GeoTIFF (BS downlink or UE uplink).")
    ap.add_argument("--dem", required=True, help="Path to a DEM GeoTIFF "
                    "(e.g. a LOLA/PGDA 5 m tile).")
    ap.add_argument("--clip-km", type=float, default=None,
                    help="Read only a square of this half-width (km) around "
                    "the tile centre. Strongly recommended for 5 m tiles.")
    ap.add_argument("--mode", choices=["bs", "ue"], default="bs")
    ap.add_argument("--tx-frac", type=float, nargs=2, default=(0.5, 0.5),
                    metavar=("ROWF", "COLF"),
                    help="Mast position as fractions of the tile (row, col); "
                    "default centre.")
    ap.add_argument("--freq-ghz", type=float, default=2.5)
    ap.add_argument("--h-tx", type=float, default=30.0,
                    help="Mast height (m). In ue mode this is still the mast "
                    "the UEs talk to.")
    ap.add_argument("--h-rx", type=float, default=2.0,
                    help="UE antenna height (m).")
    ap.add_argument("--eirp-dbm", type=float, default=None,
                    help="Transmit EIRP. Defaults: 53 (bs), 23 (ue).")
    ap.add_argument("--rx-gain-dbi", type=float, default=None,
                    help="Receive gain. Defaults: 2 (bs mode, UE antenna), "
                    "12 (ue mode, BS sector antenna).")
    ap.add_argument("--sens-dbm", type=float, default=-106.0)
    ap.add_argument("--rho", type=float, default=1.50)
    ap.add_argument("--stride", type=int, default=1,
                    help="Compute every Nth pixel (speed/resolution knob).")
    ap.add_argument("--out", default="figures/coverage_map",
                    help="Output prefix (writes <out>.png; with "
                    "--save-geotiff also <out>.tif).")
    ap.add_argument("--save-geotiff", action="store_true")
    args = ap.parse_args()

    eirp = args.eirp_dbm if args.eirp_dbm is not None else (
        53.0 if args.mode == "bs" else 23.0)
    rx_gain = args.rx_gain_dbi if args.rx_gain_dbi is not None else (
        2.0 if args.mode == "bs" else 12.0)

    dem, transform, crs = load_dem(args.dem, clip_extent_km=args.clip_km)
    px_m = abs(transform.a)
    ny, nx = dem.shape
    tx_rc = (int(round(args.tx_frac[0] * (ny - 1))),
             int(round(args.tx_frac[1] * (nx - 1))))
    print(f"DEM {args.dem}: {ny}x{nx} px @ {px_m:.1f} m; mast at {tx_rc} "
          f"(elev {dem[tx_rc]:.0f} m); mode={args.mode}, "
          f"f={args.freq_ghz} GHz, EIRP={eirp} dBm, Grx={rx_gain} dBi, "
          f"sens={args.sens_dbm} dBm")

    margin, los = compute_margin_map(
        dem, px_m, tx_rc, args.h_tx, args.h_rx, args.freq_ghz * 1e9,
        eirp, rx_gain, args.sens_dbm, args.rho, stride=args.stride)

    direction = ("BS downlink" if args.mode == "bs"
                 else f"UE uplink ({eirp:.0f} dBm terminal)")
    title = (f"{direction} — {args.freq_ghz:g} GHz, masts "
             f"{args.h_tx:.0f} m / {args.h_rx:.0f} m")
    plot_margin_map(dem, margin, los, px_m, tx_rc, args.out + ".png", title)
    if args.save_geotiff:
        save_geotiff(margin, transform, crs, args.out + ".tif")


if __name__ == "__main__":
    main()

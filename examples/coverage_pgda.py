"""
Per-band coverage maps over a REAL lunar DEM (or a labeled synthetic fallback).

Reference DEM (citable, Artemis candidate sites -- avoids "synthetic terrain"
reviewer pushback):
    PGDA LOLA 5 m/pixel South Pole DEMs, Barker et al. (2021), PSS 203 105119.
    https://pgda.gsfc.nasa.gov/products/78   (dir: /data/LOLA_5mpp/)
    Sites: Site01 Connecting Ridge, Site04 Shackleton rim, Site11 de Gerlache
    rim, Site23 Malapert massif. Files: <Site>_surf.tif (polar stereographic,
    MOON_ME/DE421, 5 m/px).

Usage:
    # real DEM (download a *_surf.tif from the product above), then:
    LUNAR_DEM=/path/to/Site01_surf.tif python examples/coverage_pgda.py
    # or synthetic fallback (labeled) if LUNAR_DEM is unset.
"""
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunarcomms import bands  # noqa: E402
from lunarcomms.coverage.link_budget import compute_coverage_map  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEM_PATH = os.environ.get("LUNAR_DEM")
CLIP_KM = float(os.environ.get("LUNAR_CLIP_KM", "10"))


def load_dem():
    if DEM_PATH and os.path.exists(DEM_PATH):
        from lunarcomms.io.pgda import load_dem as _ld
        dem, transform, crs = _ld(DEM_PATH, clip_extent_km=CLIP_KM)
        dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
        px = abs(transform[0]) if transform is not None else 5.0
        name = os.path.basename(DEM_PATH)
        return dem, (px, 0, 0, 0, -px, 0), f"PGDA LOLA 5 m/px ({name})"
    # labeled synthetic fallback (NOT for publication figures)
    n, px = 120, 40.0
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    rng = np.random.default_rng(0)
    dem = 60 * rng.standard_normal((n, n))
    from scipy.ndimage import gaussian_filter
    dem = gaussian_filter(dem, 3)
    dem += 180 * np.exp(-((xx - 80) ** 2) / (2 * 6 ** 2))
    for cx, cy, r, d in [(40, 70, 12, -220), (90, 35, 9, -150)]:
        dem += d * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2)) / (2 * r ** 2))
    return dem, (px, 0, 0, 0, -px, 0), "SYNTHETIC placeholder (swap for PGDA DEM)"


def main():
    dem, transform, label = load_dem()
    ny, nx = dem.shape
    tx = (ny // 2, nx // 4)
    # put the BTS on a local high so it has a fighting chance
    r0 = max(tx[0] - 5, 0)
    r1 = min(tx[0] + 5, ny)
    c0 = max(tx[1] - 5, 0)
    c1 = min(tx[1] + 5, nx)
    sub = dem[r0:r1, c0:c1]
    off = np.unravel_index(np.argmax(sub), sub.shape)
    tx = (r0 + off[0], c0 + off[1])

    fig, ax = plt.subplots(1, 4, figsize=(16, 4.4), constrained_layout=True)
    for a, name in zip(ax, ("UHF", "S", "Ka", "D")):
        m = compute_coverage_map(
            dem, transform, None, tx[0], tx[1], 30.0, 2.0,
            bands.freq_hz(name), 53.0, 0.0, -106.0,
            use_envelope=True, curvature=True)   # clean map, spherical Moon
        c = float(np.mean(m > 0))
        im = a.imshow(m, cmap="RdYlGn", vmin=-30, vmax=60)
        a.contour(dem, levels=8, colors="k", linewidths=0.3, alpha=0.4)
        a.plot(tx[1], tx[0], "b^", ms=9)
        a.set_title(f"{name} ({bands.freq_hz(name)/1e9:g} GHz)  cov={c:.0%}")
        a.set_xticks([])
        a.set_yticks([])
    fig.colorbar(im, ax=ax, shrink=0.8, label="link margin (dB)")
    fig.suptitle(f"Per-band coverage (envelope, spherical Moon) — DEM: {label}",
                 fontsize=12)
    out = os.path.join(HERE, "coverage_pgda.png")
    fig.savefig(out, dpi=120)
    print(f"wrote {out}\nDEM: {label}  shape={dem.shape}  TX={tx}")


if __name__ == "__main__":
    main()

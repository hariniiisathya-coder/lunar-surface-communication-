"""
2D coverage-map A/B over a real LOLA tile: LunarTwin (Sionna RT) vs LunaCov
(analytic two-ray + Deygout), one gNB on the local high, RX grid across the tile.
Saves an .npz of both link-margin maps.

Finding (Connecting Ridge, 2.5 GHz, gNB 30 m, on nuwins-rack-2 A100): the two
models BRACKET coverage -- analytic Deygout 30% (conservative) vs ray-traced
79% (permissive). The gap is a diffraction-model difference: mesh-invariant
(5 m == 15 m mesh) and not reflection-driven (specular-off ablation gives 80%).

Usage:
  LUNAR_DEM_NPY=data/site01_3km.npy LUNAR_PX=5 python examples/twin_coverage_map_pgda.py
Runs LunaCov always; the Sionna twin only if sionna-rt is importable.
"""
import os

import numpy as np

from lunarcomms.export import taps as T

HERE = os.path.dirname(os.path.abspath(__file__))
FREQ = float(os.environ.get("LUNAR_FREQ", "2.5e9"))
STRIDE = int(os.environ.get("LUNAR_STRIDE", "2"))
STEP = int(os.environ.get("LUNAR_STEP", "30"))       # RX grid step in px
MARGIN_OFFSET = 159.0    # EIRP 53 dBm + gain - sens(-106) => margin = 159 + gain


def load_dem():
    npy = os.environ.get("LUNAR_DEM_NPY")
    if npy and os.path.exists(npy):
        return np.load(npy).astype(float), float(os.environ.get("LUNAR_PX", "5"))
    tif = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
    from lunarcomms.io.pgda import load_dem as _ld
    dem, tr, _ = _ld(tif, clip_extent_km=float(os.environ.get("LUNAR_CLIP_KM", "3")))
    return np.nan_to_num(dem, nan=float(np.nanmin(dem))), abs(tr[0])


def main():
    dem, px = load_dem()
    ny, nx = dem.shape
    r0, c0 = np.unravel_index(int(np.argmax(dem)), dem.shape)
    rows, cols = range(0, ny, STEP), range(0, nx, STEP)

    tw = None
    try:
        from lunarcomms.twin import LunarTwin
        tw = LunarTwin(dem, px)
        tw.build(os.path.join(HERE, "twin_scene"), stride=STRIDE, curvature=True)
        tw.load(FREQ)
        gnb = [float(c0 * px), float(r0 * px), float(dem[r0, c0]) + 30.0]
    except (ImportError, ModuleNotFoundError):
        print("sionna-rt not installed: LunaCov-only map.")

    twin = np.full((len(list(rows)), len(list(cols))), -200.0)
    luna = np.full_like(twin, -200.0)
    for ai, r in enumerate(range(0, ny, STEP)):
        for bi, c in enumerate(range(0, nx, STEP)):
            if r == r0 and c == c0:
                twin[ai, bi] = luna[ai, bi] = 60.0
                continue
            lk = T.link_taps(dem, px, r0, c0, r, c, 30.0, 2.0, FREQ)
            clk = lk.collapsed(T.MCHEM_TAP_RESOLUTION_S)
            luna[ai, bi] = -(lk.fspl_direct_db
                             - 20 * np.log10(max(abs(clk.gains[0]), 1e-12)))
            if tw is not None:
                a, tau = tw.link_cir(gnb, [float(c * px), float(r * px),
                                           float(dem[r, c]) + 2.0],
                                     max_depth=3, diffraction=True)
                m = np.isfinite(tau) & (np.abs(a) > 0)
                a = a[m]
                if a.size:
                    twin[ai, bi] = 10 * np.log10(np.sum(np.abs(a) ** 2))

    np.savez(os.path.join(HERE, "twin_coverage_map.npz"), twin=twin, luna=luna,
             px=px, step=STEP, gnb_rc=[int(r0), int(c0)],
             margin_offset=MARGIN_OFFSET)
    lcov = float(np.mean((luna + MARGIN_OFFSET) > 0))
    msg = f"LunaCov coverage={lcov:.1%}"
    if tw is not None:
        msg += f" | twin coverage={float(np.mean((twin + MARGIN_OFFSET) > 0)):.1%}"
    print(msg + " -> examples/twin_coverage_map.npz")


if __name__ == "__main__":
    main()

"""
A/B over a real LOLA tile: LunarTwin (Sionna RT) vs LunaCov (analytic two-ray +
Deygout), along a rover radial from a gNB on the local high. Closes the paper's
"compare against ray tracing" gap: the two independent models cross-validate in
LOS and diverge in shadow (exact ray-traced diffraction vs analytic Deygout).

Validated on nuwins-rack-2 (A100, sionna-rt 2.1.0): 29 waypoints over Connecting
Ridge in ~2 s; LOS mean |twin - LunaCov| = 4.3 dB.

Usage (DEM as .npy heightfield or GeoTIFF):
  LUNAR_DEM_NPY=data/site01_3km.npy LUNAR_PX=5 python examples/twin_ab_pgda.py
  # or a GeoTIFF (needs rasterio):
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif python examples/twin_ab_pgda.py
Runs LunaCov always; the Sionna twin only if sionna-rt is importable.
"""
import json
import os

import numpy as np

from lunarcomms.export import lchem
from lunarcomms.export import taps as T
from lunarcomms.twin import LunarTwin

HERE = os.path.dirname(os.path.abspath(__file__))
FREQ = float(os.environ.get("LUNAR_FREQ", "2.5e9"))
STRIDE = int(os.environ.get("LUNAR_STRIDE", "3"))
NWP = int(os.environ.get("LUNAR_NWP", "30"))
SCENE = os.environ.get("LUNAR_SCENE_DIR", os.path.join(HERE, "twin_scene"))


def load_dem():
    npy = os.environ.get("LUNAR_DEM_NPY")
    if npy and os.path.exists(npy):
        return np.load(npy).astype(float), float(os.environ.get("LUNAR_PX", "5"))
    tif = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
    from lunarcomms.io.pgda import load_dem as _ld
    dem, tr, _ = _ld(tif, clip_extent_km=float(os.environ.get("LUNAR_CLIP_KM", "3")))
    return np.nan_to_num(dem, nan=float(np.nanmin(dem))), abs(tr[0])


def lunacov_gain_db(dem, px, r0, c0, ri, ci):
    lk = T.link_taps(dem, px, r0, c0, ri, ci, 30.0, 2.0, FREQ)
    clk = lk.collapsed(T.MCHEM_TAP_RESOLUTION_S)
    return -(lk.fspl_direct_db - 20 * np.log10(max(abs(clk.gains[0]), 1e-12))), lk.los


def main():
    dem, px = load_dem()
    ny, nx = dem.shape
    r0, c0 = np.unravel_index(int(np.argmax(dem)), dem.shape)
    rs = np.linspace(r0, ny - 1 - r0, NWP).round().astype(int)
    cs = np.linspace(c0, nx - 1 - c0, NWP).round().astype(int)

    tw = None
    try:
        tw = LunarTwin(dem, px)
        tw.build(SCENE, stride=STRIDE, curvature=True)
        tw.load(FREQ)
        gnb = [c0 * px, r0 * px, float(dem[r0, c0]) + 30.0]
    except (ImportError, ModuleNotFoundError):
        print("sionna-rt not installed: LunaCov-only run.")

    res = {"dist_m": [], "twin_gain_db": [], "twin_npaths": [],
           "lunacov_gain_db": [], "los": []}
    frames = []
    for ri, ci in zip(rs, cs):
        if ri == r0 and ci == c0:
            continue
        d = float(np.hypot(ri - r0, ci - c0) * px)
        lc_gain, los = lunacov_gain_db(dem, px, r0, c0, ri, ci)
        tw_gain, npaths = float("nan"), 0
        if tw is not None:
            rx = [ci * px, ri * px, float(dem[ri, ci]) + 2.0]
            a, tau = tw.link_cir(gnb, rx, max_depth=3, diffraction=True)
            m = np.isfinite(tau) & (np.abs(a) > 0)
            a = a[m]
            tw_gain = 10 * np.log10(np.sum(np.abs(a) ** 2)) if a.size else -200.0
            npaths = int(a.size)
            frames.append([lchem.to_lchem_pdp(
                tw.link_taps(gnb, rx, FREQ, max_depth=3, diffraction=True))])
        res["dist_m"].append(d)
        res["twin_gain_db"].append(tw_gain)
        res["twin_npaths"].append(npaths)
        res["lunacov_gain_db"].append(float(lc_gain))
        res["los"].append(bool(los))

    with open(os.path.join(HERE, "twin_ab.json"), "w") as f:
        json.dump(res, f)
    if frames:
        lchem.save_lchem_json(frames, os.path.join(HERE, "twin_ab_mt012.json"))
    los = np.array(res["los"])
    if tw is not None and los.any():
        dd = np.abs(np.array(res["twin_gain_db"]) - np.array(res["lunacov_gain_db"]))
        print(f"LOS mean |twin - LunaCov| = {np.nanmean(dd[los]):.1f} dB")
    print(f"{len(res['dist_m'])} waypoints -> examples/twin_ab.json")


if __name__ == "__main__":
    main()

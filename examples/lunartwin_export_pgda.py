"""
LunarTwin over a real LOLA tile -> Sionna RT CIRs -> LCHEM MT-012 (second CIR
source, alongside LunaCov). The scene build runs without Sionna; the ray-trace
+ export runs only if Sionna RT is installed.

Usage:
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif \
      python examples/lunartwin_export_pgda.py
"""
import os

import numpy as np

from lunarcomms import bands
from lunarcomms.export import lchem
from lunarcomms.twin import LunarTwin

HERE = os.path.dirname(os.path.abspath(__file__))
DEM = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
BAND = os.environ.get("LUNAR_BAND", "S")
CLIP_KM = float(os.environ.get("LUNAR_CLIP_KM", "4"))
STRIDE = int(os.environ.get("LUNAR_STRIDE", "4"))   # LOD for tractability


def load():
    if os.path.exists(DEM):
        from lunarcomms.io.pgda import load_dem
        dem, tr, _ = load_dem(DEM, clip_extent_km=CLIP_KM)
        dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
        return dem, abs(tr[0]), os.path.basename(DEM)
    return np.random.default_rng(0).standard_normal((200, 200)) * 30, 5.0, "synthetic"


def main():
    dem, px, name = load()
    f = bands.freq_hz(BAND)
    tw = LunarTwin(dem, pixel_size_m=px)
    out = tw.build(os.path.join(HERE, f"twin_{os.path.splitext(name)[0]}"),
                   stride=STRIDE, curvature=True)
    print(f"{name}: scene built -> {out['n_verts']} verts, {out['n_faces']} faces "
          f"(stride {STRIDE}, {px*STRIDE:.0f} m mesh)")
    print(f"  ply={out['ply']}\n  xml={out['xml']}")

    # gNB on a local high; one UE on the surface.
    ny, nx = dem.shape
    tx = np.unravel_index(np.argmax(dem), dem.shape)
    gnb = [tx[1] * px, tx[0] * px, float(dem[tx]) + 30.0]
    uj = min(tx[1] + 40, nx - 1)
    ue = [uj * px, tx[0] * px, float(dem[tx[0], uj]) + 2.0]

    try:
        tw.load(freq_hz=f)
        lk = tw.link_taps(gnb, ue, f, max_depth=3, diffraction=True)
        pdp = lchem.to_lchem_pdp(lk, lchem.GNB, lchem.UE1, mode="complex16")
        print(f"  Sionna RT: {lk.meta.get('n_paths')} paths -> "
              f"{len(pdp['coeffs'])} LCHEM taps, delays_10ns={pdp['delays_10ns']}, "
              f"shiftright={pdp['shiftright_bits']}b")
        print("  -> feeds the same MT-012 slot as LunaCov (A/B on one emulator)")
    except (ImportError, ModuleNotFoundError):
        print("  Sionna RT not installed: scene ready; install sionna to ray-trace.")


if __name__ == "__main__":
    main()

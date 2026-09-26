"""Margin maps at the paper's standard: 10 km tile (clip_extent_km=5), BTS on the
tile maximum, 30 m / 2 m, EIRP 53 dBm, Grx 2 dBi, sensitivity -106 dBm, stride 2.
Saves one .npz per site with UHF/S/Ka margin maps and the LOS mask; the paper's
coverage maps, margin histogram and three-band figure are plotted from these.
Usage: python analysis/paper_margin_maps_10km.py Site01 <out_dir>"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from coverage_map import compute_margin_map
from lunarcomms.io.pgda import load_dem

site, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
dem, tr, _ = load_dem(f"data/dem/{site}/{site}_final_adj_5mpp_surf.tif", clip_extent_km=5.0)
px = abs(tr.a)
tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
res = {}
for name, f in (("UHF", 0.442e9), ("S", 2.5e9), ("Ka", 27.0e9)):
    t = time.time()
    m, los = compute_margin_map(dem, px, tx, 30.0, 2.0, f, 53.0, 2.0, -106.0, 1.5, stride=2)
    res[name] = m
    fin = m[::2, ::2]; fin = fin[np.isfinite(fin)]
    print(f"{site} {name}: coverage {100*np.mean(fin > 0):.1f}% ({time.time()-t:.0f}s)", flush=True)
np.savez_compressed(f"{out}/{site}_margin_10km.npz", dem=dem, px=px, tx=np.array(tx),
                    los=los, UHF=res["UHF"], S=res["S"], Ka=res["Ka"])
print("DONE", site, flush=True)

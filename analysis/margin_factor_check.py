"""Factor checks for the margin distribution and cell-edge results (paper Sec. Handover).

Used to trace the old "+45/-109 dB bimodal" numbers (examples/planner_analysis_pgda.py:
20 km tile, DEM block-averaged to ~185 m, BTS at a local high, Grx 0) and to test
the 10 km results against curvature, extent, DEM resolution and DEM error.
Run from the repo root:  python analysis/margin_factor_check.py --out <prefix> [...]

Same physics as analysis/coverage_map.compute_margin_map (LOS: exact two-ray;
NLOS: FSPL + Deygout), with switches to isolate each factor:
  --curv    add the spherical bulge d1 d2 / (2 R) to the Deygout profile
  --clip    half-width of the tile (km): 5 -> 10 km tile, 10 -> 20 km tile
  --block   block-mean the DEM by this factor first (old run: ~36 -> 182 m px)
  --stride  evaluate every stride-th pixel (profiles still at DEM resolution)
  --noise   add N(0, noise) m to every DEM pixel (DEM-error test; --seed)
  --tx      'max' (tile maximum, paper standard) or 'old' (local high near
            (ny/2, nx/4), as examples/planner_analysis_pgda.py)
Writes <out>.npz (margin on the evaluated grid, los) and prints stats.
"""
import argparse, json, time
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import (los_mask_from_tx, extract_profile,
                                         curvature_drop_m, R_MOON_M)
from lunarcomms.propagation import two_ray, friis, diffraction

ap = argparse.ArgumentParser()
ap.add_argument("--site", default="Site01")
ap.add_argument("--clip", type=float, default=5.0)
ap.add_argument("--block", type=int, default=1)
ap.add_argument("--stride", type=int, default=2)
ap.add_argument("--curv", type=int, default=1)
ap.add_argument("--tx", default="max")
ap.add_argument("--bands", default="S")
ap.add_argument("--grx", type=float, default=2.0)
ap.add_argument("--noise", type=float, default=0.0)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", required=True)
a = ap.parse_args()

dem, tr, _ = load_dem(f"data/dem/{a.site}/{a.site}_final_adj_5mpp_surf.tif", clip_extent_km=a.clip)
px = abs(tr.a)
if a.block > 1:
    dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
    b = a.block; ny, nx = dem.shape
    dem = dem[:ny // b * b, :nx // b * b].reshape(ny // b, b, nx // b, b).mean((1, 3))
    px *= b
ny, nx = dem.shape
if a.noise > 0:
    dem0 = dem.copy()
if a.tx == "max":
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
else:
    r, c, rad = ny // 2, nx // 4, max(5, int(round(5 * 182 / px)))
    sub = dem[max(r - rad, 0):r + rad, max(c - rad, 0):c + rad]
    o = np.unravel_index(np.nanargmax(sub), sub.shape)
    tx = (max(r - rad, 0) + o[0], max(c - rad, 0) + o[1])
if a.noise > 0:  # DEM error realization, BTS kept at the same pixel
    dem = dem0 + np.random.default_rng(a.seed).normal(0, a.noise, dem0.shape)
F = {"UHF": 0.442e9, "S": 2.5e9, "Ka": 27e9}
H_TX, H_RX, EIRP, SENS, RHO = 30.0, 2.0, 53.0, -106.0, 1.5
t0 = time.time()
los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
tx_elev = dem[tx] + H_TX
rows = range(0, ny, a.stride); cols = range(0, nx, a.stride)
res = {"los": los[::a.stride, ::a.stride], "px": px * a.stride, "tx": np.array(tx) // a.stride}
stats = {"args": vars(a), "px_dem": px, "tx": tx, "shape": [ny, nx]}
for band in a.bands.split(","):
    f = F[band]; m = np.full((len(rows), len(cols)), np.nan)
    for ii, i in enumerate(rows):
        for jj, j in enumerate(cols):
            if np.isnan(dem[i, j]):
                continue
            if (i, j) == tx:
                m[ii, jj] = EIRP + a.grx - SENS; continue
            dh = float(np.hypot(i - tx[0], j - tx[1]) * px)
            if los[i, j]:
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, f, RHO))
            else:
                d3 = float(np.hypot(dh, dem[i, j] + H_RX - tx_elev))
                pl = float(friis.fspl_db(d3, f))
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                if a.curv and dist[-1] > 0:
                    h = h + curvature_drop_m(dist, dist[-1], R_MOON_M)
                pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, f))
            m[ii, jj] = EIRP - pl + a.grx - SENS
    res[band] = m
    fin = np.isfinite(m); L = res["los"]
    v = m[fin]; srv = fin & (m > 0)
    stats[band] = {
        "coverage": 100 * np.mean(v > 0), "los_pct": 100 * np.mean(L[fin]),
        "med_served": float(np.median(v[v > 0])), "med_unserved": float(np.median(v[v <= 0])),
        "med_los": float(np.median(m[fin & L])), "med_nlos": float(np.median(m[fin & ~L])),
        "nlos_share_of_served": 100 * float(np.mean(~L[srv])),
        "within10": 100 * float(np.mean(np.abs(v) < 10)),
        "t_s": round(time.time() - t0)}
    print(band, json.dumps(stats[band]), flush=True)
np.savez_compressed(a.out + ".npz", **res)
json.dump(stats, open(a.out + ".json", "w"), indent=1, default=float)
print("DONE", a.out, flush=True)

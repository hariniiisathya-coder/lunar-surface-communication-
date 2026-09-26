"""LunarTwin vs LunaCov at the paper's standardized 10 km Connecting Ridge tile.
Same budget as the planner (EIRP 53 dBm, Grx 2 dBi, sens -106 dBm -> offset 161 dB),
gNB 30 m on the tile's highest point, UE 2 m, RX grid every STEP px.
Runs: opaque twin (refraction off) at UHF/S/Ka + transmissive twin (refraction on)
at S-band; LunaCov on the same grid; strict LOS fraction on the same grid.
"""
import sys, time, json, numpy as np
sys.path.insert(0, "/mnt/nuwinsshared/lunacov/repo")
from lunarcomms.twin import LunarTwin
from lunarcomms.export import taps as T
from lunarcomms.geometry.horizon import los_mask_from_tx

BASE = "/mnt/nuwinsshared/lunacov"
dem = np.load(f"{BASE}/data/site01_5km.npy").astype(float)
px, STRIDE, STEP = 5.0, 3, 20
OFF = 53.0 + 2.0 + 106.0
ny, nx = dem.shape
r0, c0 = np.unravel_index(int(np.argmax(dem)), dem.shape)
rows, cols = list(range(0, ny, STEP)), list(range(0, nx, STEP))
print(f"DEM {dem.shape} tx=({r0},{c0}) grid {len(rows)}x{len(cols)} mesh {px*STRIDE:.0f} m", flush=True)

los = los_mask_from_tx(dem, px, int(r0), int(c0), 30.0, 2.0)
los_g = np.array([[bool(los[r, c]) for c in cols] for r in rows])
print(f"strict LOS fraction on grid: {100*los_g.mean():.1f}%", flush=True)

t0 = time.time()
tw = LunarTwin(dem, px)
info = tw.build(f"{BASE}/scene_10km", stride=STRIDE, curvature=True)
print(f"mesh: {info['n_verts']} verts, {info['n_faces']} faces ({time.time()-t0:.0f}s)", flush=True)
gnb = [float(c0 * px), float(r0 * px), float(dem[r0, c0]) + 30.0]
demc = np.array([[dem[r, c] for c in cols] for r in rows])


def run(freq, refraction):
    tw.load(freq)
    tw_m = np.full((len(rows), len(cols)), -300.0)
    lc_m = np.full_like(tw_m, -300.0)
    npaths = np.zeros_like(tw_m)
    t = time.time()
    for ai, r in enumerate(rows):
        for bi, c in enumerate(cols):
            if r == r0 and c == c0:
                tw_m[ai, bi] = lc_m[ai, bi] = 60.0
                continue
            a, tau = tw.link_cir(gnb, [float(c * px), float(r * px), float(dem[r, c]) + 2.0],
                                 max_depth=3, diffraction=True, refraction=refraction)
            m = np.isfinite(tau) & (np.abs(a) > 0)
            a = a[m]
            npaths[ai, bi] = a.size
            if a.size:
                tw_m[ai, bi] = 10 * np.log10(np.sum(np.abs(a) ** 2))
            lk = T.link_taps(dem, px, r0, c0, r, c, 30.0, 2.0, freq)
            clk = lk.collapsed(T.MCHEM_TAP_RESOLUTION_S)
            lc_m[ai, bi] = -(lk.fspl_direct_db - 20 * np.log10(max(abs(clk.gains[0]), 1e-12)))
        if ai % 20 == 0:
            print(f"   row {ai}/{len(rows)} ({time.time()-t:.0f}s)", flush=True)
    return tw_m, lc_m, npaths, time.time() - t


res = {"grid_step_m": STEP * px, "mesh_m": STRIDE * px, "offset_db": OFF,
       "los_frac": float(los_g.mean()), "tx_rc": [int(r0), int(c0)]}
for name, f, refr in [("UHF", 0.442e9, False), ("S", 2.5e9, False), ("Ka", 27e9, False),
                      ("S_refraction", 2.5e9, True)]:
    tw_m, lc_m, npaths, dt = run(f, refr)
    served_t, served_l = (tw_m + OFF) > 0, (lc_m + OFF) > 0
    shadow = ~los_g
    r = {"freq_hz": f, "refraction": refr,
         "twin_cov": float(served_t.mean()), "lunacov_cov": float(served_l.mean()),
         "twin_served_in_shadow": float((served_t & shadow).sum() / shadow.sum()),
         "lunacov_served_in_shadow": float((served_l & shadow).sum() / shadow.sum()),
         "twin_served_in_los": float((served_t & los_g).sum() / los_g.sum()),
         "twin_zero_path_frac": float((npaths == 0).mean()), "seconds": dt}
    both = (tw_m > -299) & los_g
    if both.any():
        d = (tw_m - lc_m)[both]
        r["los_gain_diff_db_mean"] = float(np.mean(d)); r["los_gain_diff_db_absmean"] = float(np.mean(np.abs(d)))
    res[name] = r
    np.savez(f"{BASE}/out/twin10km_{name}.npz", twin=tw_m, luna=lc_m, npaths=npaths, los=los_g,
             demc=demc, step=STEP, px=px, gnb_rc=[int(r0), int(c0)], margin_offset=OFF)
    print(f"{name}: twin {100*r['twin_cov']:.1f}% | lunacov {100*r['lunacov_cov']:.1f}% | "
          f"LOS {100*res['los_frac']:.1f}% | twin-in-shadow {100*r['twin_served_in_shadow']:.1f}% | "
          f"luna-in-shadow {100*r['lunacov_served_in_shadow']:.1f}% ({dt:.0f}s)", flush=True)
    json.dump(res, open(f"{BASE}/out/twin10km.json", "w"), indent=2)
print("DONE twin10km", flush=True)

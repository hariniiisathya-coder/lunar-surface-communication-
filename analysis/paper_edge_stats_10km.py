"""Margin-distribution and cell-edge statistics for the paper (Sec. Handover),
from the 10 km margin maps of analysis/paper_margin_maps_10km.py.

Per band: coverage, LOS share, median margin of LOS / NLOS / served / unserved
pixels, NLOS share of the served area, and the same coverage with the NLOS loss
shifted by +/-10 dB (the terrestrial-analog error). For S-band, statistics along
1440 radials from the BTS at the 10 m grid spacing: at each outward crossing of
the 0 dB threshold, the further decrease of margin over the next 50/100/200 m,
whether the path re-enters coverage within 200 m, the distance between the last
+10 dB and the first -10 dB sample, and the margin step across LOS->NLOS.
Usage: python analysis/paper_edge_stats_10km.py <figs10_dir> Site01 [Site04]
"""
import json
import sys

import numpy as np


def radial_stats(m, los, px, tx, n_az=1440):
    ny, nx = m.shape
    out = {"drop50": [], "drop100": [], "drop200": [], "reentry200": [], "w20": [], "los_step": []}
    s_all = np.arange(1, 4 * max(ny, nx)) * px
    for az in np.linspace(0, 2 * np.pi, n_az, endpoint=False):
        r = tx[0] + s_all / px * np.sin(az); c = tx[1] + s_all / px * np.cos(az)
        k = (r >= 0) & (r <= ny - 1) & (c >= 0) & (c <= nx - 1)
        r, c, s = np.rint(r[k]).astype(int), np.rint(c[k]).astype(int), s_all[k]
        v, L = m[r, c], los[r, c]
        g = np.isfinite(v); v, L, s = v[g], L[g], s[g]
        for i in range(1, len(v)):
            if L[i - 1] and not L[i]:
                out["los_step"].append(v[i - 1] - v[i])
            if not (v[i - 1] > 0 >= v[i]):
                continue
            for d, key in ((50, "drop50"), (100, "drop100"), (200, "drop200")):
                j = np.searchsorted(s, s[i] + d)
                if j < len(v):
                    out[key].append(v[i] - v[j])
            j = np.searchsorted(s, s[i] + 200)
            if j < len(v):
                out["reentry200"].append(float(np.any(v[i:j] > 0)))
            a = i - 1
            while a > 0 and v[a] < 10:
                a -= 1
            b = i
            while b < len(v) - 1 and v[b] > -10:
                b += 1
            if v[a] >= 10 and v[b] <= -10:
                out["w20"].append(s[b] - s[a])
    res = {"crossings_per_radial": len(out["drop50"]) / n_az}
    for k, x in out.items():
        x = np.asarray(x, float)
        res[k] = ({"pct": 100 * x.mean(), "n": len(x)} if k == "reentry200" else
                  {"p10": np.percentile(x, 10), "median": np.median(x), "p90": np.percentile(x, 90), "n": len(x)})
    return res


def site_stats(path):
    D = np.load(path)
    los, px, tx = D["los"][::2, ::2].astype(bool), 2 * float(D["px"]), D["tx"] // 2
    res = {}
    for b in ("UHF", "S", "Ka"):
        m = D[b][::2, ::2]; fin = np.isfinite(m); v = m[fin]; L = los[fin]
        r = {"coverage": 100 * np.mean(v > 0), "los_pct": 100 * L.mean(),
             "med_los": np.median(v[L]), "med_nlos": np.median(v[~L]),
             "med_served": np.median(v[v > 0]), "med_unserved": np.median(v[v <= 0]),
             "nlos_share_of_served": 100 * np.mean(~L[v > 0]),
             "los_served_pct": 100 * np.mean(v[L] > 0)}
        for sh in (-10, 10):  # sh = error of the predicted NLOS loss
            mv = np.where(L, v, v - sh)
            r[f"coverage_nlos{sh:+d}dB"] = 100 * np.mean(mv > 0)
            r[f"nlos_share_nlos{sh:+d}dB"] = 100 * np.mean(~L[mv > 0])
        res[b] = r
    res["S_radial"] = radial_stats(D["S"][::2, ::2], los, px, tx)
    return res


if __name__ == "__main__":
    d = sys.argv[1]
    out = {s: site_stats(f"{d}/{s}_margin_10km.npz") for s in sys.argv[2:]}
    txt = json.dumps(out, indent=1, default=lambda x: round(float(x), 2))
    print(txt)
    open(f"{d}/edge_stats_10km.json", "w").write(txt)

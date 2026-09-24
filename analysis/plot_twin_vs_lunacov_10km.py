"""Figure: LunaCov vs LunarTwin coverage at the 10 km Connecting Ridge tile.
(a) LunaCov served map, (b) opaque twin, (c) transmissive twin (refraction on),
all S-band, plus (d) served fraction per band vs the strict LOS set."""
import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

D = sys.argv[1]           # directory with twin10km_*.npz and twin10km.json
OUT = sys.argv[2]
res = json.load(open(f"{D}/twin10km.json"))
S = np.load(f"{D}/twin10km_S.npz")
R = np.load(f"{D}/twin10km_S_refraction.npz")
off = float(S["margin_offset"])
step, px = int(S["step"]), float(S["px"])
demc = S["demc"]
n = demc.shape[0]
ext = [0, n * step * px / 1e3, n * step * px / 1e3, 0]
shade = LightSource(azdeg=315, altdeg=35).hillshade(demc, vert_exag=2, dx=step * px, dy=step * px)
g = S["gnb_rc"]
gx, gy = g[1] * px / 1e3, g[0] * px / 1e3

fig = plt.figure(figsize=(13.2, 3.9))
panels = [("(a) LunaCov (analytic)", S["luna"], res["S"]["lunacov_cov"]),
          ("(b) LunarTwin, opaque terrain", S["twin"], res["S"]["twin_cov"]),
          ("(c) LunarTwin, refraction on", R["twin"], res["S_refraction"]["twin_cov"])]
im = None
for k, (title, m, cov) in enumerate(panels):
    ax = fig.add_subplot(1, 4, k + 1)
    ax.imshow(shade, cmap="gray", extent=ext, interpolation="bilinear")
    marg = np.ma.masked_less_equal(m + off, 0.0)
    im = ax.imshow(marg, cmap="viridis", extent=ext, vmin=0, vmax=90, alpha=0.8,
                   interpolation="nearest")
    ax.plot(gx, gy, "^", color="red", ms=8, mec="white")
    ax.set_title(f"{title}\nserved {100*cov:.1f}%", fontsize=9.5)
    ax.set_xlabel("east (km)", fontsize=8.5)
    if k == 0:
        ax.set_ylabel("south (km)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
cb = fig.colorbar(im, ax=fig.axes, shrink=0.8, pad=0.01, location="left", anchor=(0, 0.5))
cb.remove()

ax = fig.add_subplot(1, 4, 4)
bands = ["UHF", "S", "Ka"]
x = np.arange(len(bands))
w = 0.26
los = 100 * res["los_frac"]
tw = [100 * res[b]["twin_cov"] for b in bands]
lc = [100 * res[b]["lunacov_cov"] for b in bands]
ax.bar(x - w, [los] * 3, w, color="0.6", label="strict LOS set")
ax.bar(x, tw, w, color="#1f77b4", label="LunarTwin (opaque)")
ax.bar(x + w, lc, w, color="#d62728", label="LunaCov")
ax.axhline(100 * res["S_refraction"]["twin_cov"], color="#1f77b4", ls="--", lw=1.2)
ax.text(2.45, 100 * res["S_refraction"]["twin_cov"] + 1.5, "twin, refraction on (S)",
        fontsize=7.5, color="#1f77b4", ha="right")
for xi, v in zip(x + w, lc):
    ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=7.5)
for xi, v in zip(x, tw):
    ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=7.5)
ax.set_xticks(x)
ax.set_xticklabels(["UHF\n0.442 GHz", "S\n2.5 GHz", "Ka\n27 GHz"], fontsize=8)
ax.set_ylabel("served fraction of tile (%)", fontsize=8.5)
ax.set_ylim(0, max(100 * res["S_refraction"]["twin_cov"], max(lc)) + 12)
ax.set_title("(d) Served area by band", fontsize=9.5)
ax.legend(fontsize=7.5, loc="center right", bbox_to_anchor=(1.0, 0.6))
ax.tick_params(labelsize=7.5)
ax.grid(axis="y", alpha=0.3)
fig.subplots_adjust(left=0.04, right=0.99, wspace=0.28, bottom=0.14, top=0.86)
sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0, 90))
cax = fig.add_axes([0.04, 0.03, 0.66, 0.025])
c2 = fig.colorbar(sm, cax=cax, orientation="horizontal")
c2.set_label("link margin (dB), served links only", fontsize=8)
c2.ax.tick_params(labelsize=7)
fig.subplots_adjust(bottom=0.24)
plt.savefig(OUT, dpi=170, bbox_inches="tight")
print("wrote", OUT)

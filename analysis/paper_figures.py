"""
Figures for the IEEE Aerospace 2027 paper, at their final printed size.

The conference format requires that no lettering in a figure be smaller than
10 pt. Every figure here is drawn at the width it is placed at in the paper
(COL = one column, 3.375 in; FULL = two columns, 7.0 in) with Times-like text at
10 pt, saved without bounding-box trimming so LaTeX places it at scale 1.

Usage: python analysis/paper_figures.py <name> [<name> ...] | all

Inputs (directory $PAPER_FIG_DATA):
  figs10/<Site>_margin_10km.npz  analysis/paper_margin_maps_10km.py <Site> figs10
  figs10/tput_ue.npz             analysis/throughput_maps_10km.py --mode ue --stride 4
                                   --dem data/dem/Site01/Site01_final_adj_5mpp_surf.tif
                                   --clip-km 5.0 --tx-frac 0.547274 0.442721
                                   --out figs10/tput_ue.png   (tx-frac = tile maximum)
  figs10/eirp_curves.json        analysis/coverage_vs_eirp_10km.py figs10
  twin10km/                      LunaTwin 10 km run (twin10km.json, twin10km_S*.npz)
  its/out/                       lunar-channel-emulation analysis/its_low_antenna_validation.py
The BLER figure parses the log of `matlab -batch regen_light` in matlab/ ($BLER_LOG); the AMC figure
reads matlab/amc_per_mcs.csv and amc_throughput_curve.csv from run_amc_curve.m.
"""
from __future__ import annotations

import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from matplotlib.text import Text

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PAPER_FIGS = os.environ.get("PAPER_FIGS",
                            "/Users/e.baena/lunar/lunar-coverage-planner-paper/figures")
DATA = os.environ.get("PAPER_FIG_DATA",
                      "/Users/e.baena/lunar/lunacov-figdata")
COL, FULL = 3.375, 7.0
PT = 10
INK, MUTED = "#1f1f1f", "#6b6b6b"
BANDC = {"UHF": "#2a78d6", "S": "#eb6834", "Ka": "#1baf7a"}


def style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": PT, "axes.titlesize": PT, "axes.labelsize": PT,
        "xtick.labelsize": PT, "ytick.labelsize": PT, "legend.fontsize": PT,
        "figure.titlesize": PT, "axes.titleweight": "normal",
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
        "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 1.4, "legend.frameon": False, "figure.dpi": 100,
        "savefig.dpi": 300, "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    })


def enforce_min_font(fig, pt=PT):
    for t in fig.findobj(Text):
        if t.get_text() and t.get_fontsize() < pt:
            t.set_fontsize(pt)


def save(fig, name, w, h):
    fig.set_size_inches(w, h)
    enforce_min_font(fig)
    out = os.path.join(PAPER_FIGS, name)
    fig.savefig(out, dpi=300, facecolor="white")      # no bbox trimming: exact size
    plt.close(fig)
    print(f"wrote {out} ({w} x {h} in)")


def hillshade(dem, px):
    return LightSource(azdeg=315, altdeg=35).hillshade(dem, vert_exag=2, dx=px, dy=px)


# --------------------------------------------------------------------- figures
def fig_sites():
    from lunarcomms.io.pgda import load_dem
    fig = plt.figure()
    for k, (sid, name) in enumerate((("Site01", "Connecting Ridge"), ("Site04", "Shackleton rim"))):
        dem, tr, _ = load_dem(f"{REPO}/data/dem/{sid}/{sid}_final_adj_5mpp_surf.tif", clip_extent_km=5.0)
        px = abs(tr.a); tx = np.unravel_index(np.nanargmax(dem), dem.shape)
        s = 10; z = dem[::s, ::s]; y, x = np.mgrid[0:z.shape[0], 0:z.shape[1]] * px * s / 1e3
        ax = fig.add_axes([0.5 * k - 0.02, -0.04, 0.5, 1.02], projection="3d"); ax.computed_zorder = False
        rgb = LightSource(azdeg=315, altdeg=40).shade(z, cmap=plt.cm.gist_earth, vert_exag=1.0, blend_mode="soft")
        ax.plot_surface(x, y, z / 1e3, facecolors=rgb, rstride=1, cstride=1, linewidth=0,
                        antialiased=False, shade=False, zorder=1)
        xt, yt, zt = tx[1] * px / 1e3, tx[0] * px / 1e3, dem[tx] / 1e3
        ax.plot([xt, xt], [yt, yt], [zt, zt + 0.5], color="red", lw=2, zorder=10)
        ax.scatter([xt], [yt], [zt + 0.5], color="red", s=30, marker="v", depthshade=False, zorder=11)
        ax.set_xlabel("East (km)", labelpad=-2); ax.set_ylabel("South (km)", labelpad=-2)
        ax.set_zlabel("Height (km)", labelpad=-2)
        ax.set_xticks([0, 5, 10]); ax.set_yticks([0, 5, 10])
        ax.tick_params(pad=-2)
        fig.text(0.5 * k + 0.23, 0.95, f"({'ab'[k]}) {name}", ha="center", va="top")
        ax.view_init(elev=38, azim=-60); ax.set_box_aspect((1, 1, 0.4), zoom=0.92)
    save(fig, "sites_3d.png", FULL, 3.0)


def fig_validation():
    """Same computations as analysis/make_validation_figures.py, laid out for print."""
    sys.path.insert(0, HERE)
    import make_validation_figures as mv
    from lunarcomms.propagation import diffraction, friis, two_ray
    from lunarcomms.regolith import dielectric as di
    H_TX, H_RX, RHO, F = mv.H_TX, mv.H_RX, mv.RHO, mv.F_S
    fig, ((a, b), (c, d)) = plt.subplots(2, 2, constrained_layout=True)
    leg = dict(borderaxespad=0.3, handlelength=1.6, frameon=True, framealpha=0.9, edgecolor="none")
    # (a) two-ray vs free space
    dd = np.logspace(1.5, 4.3, 1200); d0 = two_ray.breakpoint_distance(H_TX, H_RX, F)
    asym = 40 * np.log10(dd) - 20 * np.log10(H_TX * H_RX)
    a.semilogx(dd, two_ray.path_loss_db(dd, H_TX, H_RX, F), lw=1.0, color="#2a78d6", label="Two-ray")
    a.semilogx(dd, friis.fspl_db(np.hypot(dd, H_TX - H_RX), F), "--", color="#eb6834", label="Free space")
    a.semilogx(dd[dd > 2 * d0], asym[dd > 2 * d0], ":", lw=2, color="#1baf7a",
               label=r"$40\log d - 20\log(h_t h_r)$")
    a.axvline(d0, color=MUTED, lw=0.8)
    a.text(d0 * 1.08, 0.97, f"$d_0$ = {d0/1e3:.1f} km", transform=a.get_xaxis_transform(), va="top")
    a.set_ylim(150, 62); a.set_xlabel("Ground distance (m)"); a.set_ylabel("Path loss (dB)")
    a.set_title("(a) Two-ray model"); a.legend(loc="lower left", **leg)
    # (b) knife edge
    nu = np.linspace(-1.5, 5.0, 600)
    b.plot(nu, mv.exact_knife_edge_db(nu), lw=1.8, color="#2a78d6", label="Exact")
    b.plot(nu, diffraction.knife_edge_loss_db(nu), "--", color="#eb6834", label="ITU-R P.526")
    b.axvline(-0.78, color=MUTED, lw=0.8)
    b.text(-0.70, 0.97, r"$\nu=-0.78$", transform=b.get_xaxis_transform(), va="top")
    b.set_xlabel(r"Fresnel-Kirchhoff parameter $\nu$"); b.set_ylabel("Diffraction loss (dB)")
    b.set_title("(b) Knife-edge loss"); b.legend(loc="lower right", **leg)
    # (c) Fresnel reflection
    th = np.radians(np.linspace(0.2, 90.0, 800))
    gv, gh = di.fresnel_coefficients(RHO, F / 1e9, th)
    gv15, _ = di.fresnel_coefficients(np.log(15.0) / np.log(1.919), F / 1e9, th)
    c.plot(np.degrees(th), np.abs(gv), color="#2a78d6", label=r"$|\Gamma_V|$, regolith")
    c.plot(np.degrees(th), np.abs(gh), color="#eb6834", label=r"$|\Gamma_H|$, regolith")
    c.plot(np.degrees(th), np.abs(gv15), ":", color="#1baf7a", lw=1.8, label=r"$|\Gamma_V|$, moist soil")
    thb = np.degrees(th[np.argmin(np.abs(gv))])
    c.axvline(thb, color=MUTED, lw=0.8)
    c.text(thb + 1.5, 0.97, f"{thb:.0f}$^\\circ$", transform=c.get_xaxis_transform(), va="top")
    c.set_xlabel("Grazing angle (deg)"); c.set_ylabel(r"$|\Gamma|$"); c.set_ylim(0, 1.05)
    c.set_title("(c) Fresnel reflection"); c.legend(loc="upper right", **leg)
    # (d) loss tangent
    f = np.logspace(np.log10(0.3), np.log10(40.0), 400)
    d.loglog(f, di.loss_tangent(RHO, f), lw=1.8, color="#2a78d6", label="Siegler model (used)")
    d.loglog(f, di.loss_tangent_ab(-3.79, 0.069, f), "--", color=MUTED, label="No density term")
    pub = {"Mare Tranq.": (-3.208, -0.0422, 0.00568, "#e34948"),
           "Mare Seren.": (-3.351, -0.0811, 0.00378, "#eda100"),
           "Farside highl.": (-3.745, 0.0663, 0.00208, "#4a3aa7")}
    for name, (aa, bb, td, col) in pub.items():
        d.loglog(f, di.loss_tangent_ab(aa, bb, f), lw=0.7, color=col, alpha=0.6)
        d.plot(2.5, td, "o", ms=5, color=col)
        d.annotate(name, (2.5, td), textcoords="offset points", xytext=(-6, 0), ha="right", va="center")
    d.set_xlabel("Frequency (GHz)"); d.set_ylabel(r"$\tan\delta$")
    d.set_ylim(1.0e-3, 1.2e-2)
    d.set_title("(d) Loss tangent"); d.legend(loc="lower right", **leg)
    save(fig, "validation_baselines.png", FULL, 5.4)


def fig_regolith():
    from lunarcomms import bands
    from lunarcomms.io.pgda import sample_loss_tangent_params
    from lunarcomms.propagation import two_ray
    sys.path.insert(0, os.path.join(REPO, "examples"))
    from variable_regolith_pgda import site_latlon
    dem = f"{REPO}/data/dem/Site04/Site04_final_adj_5mpp_surf.tif"
    lat, lon = site_latlon(dem)
    ap, bp = map(float, sample_loss_tangent_params(lat, lon, f"{REPO}/data/siegler/a_prime.txt",
                                                  f"{REPO}/data/siegler/b_prime.txt"))
    d = np.linspace(40, 3000, 400)
    fig, ax = plt.subplots(constrained_layout=True)
    for nm in ("UHF", "S"):
        f = bands.freq_hz(nm)
        ax.plot(d / 1e3, two_ray.path_loss_spatial_db(d, 30.0, 2.0, f, ap, bp)
                - two_ray.path_loss_db(d, 30.0, 2.0, f), color=BANDC[nm], label=nm)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("Distance (km)"); ax.set_ylabel("Path-loss difference (dB)")
    ax.legend(title="Site-specific minus uniform", loc="lower right")
    save(fig, "regolith_Site04_final_adj_5mpp_surf.png", COL, 2.5)


def fig_specular():
    from lunarcomms import bands
    from lunarcomms.propagation import roughness
    freqs = np.logspace(np.log10(0.3e9), np.log10(200e9), 400)
    theta = np.deg2rad(5.0)
    fig, ax = plt.subplots(constrained_layout=True)
    for s_cm, c in ((0.5, "#86b6ef"), (1.0, "#3987e5"), (2.0, "#1c5cab"), (5.0, "#0d366b")):
        ax.semilogx(freqs / 1e9, roughness.specular_factor(s_cm / 100.0, freqs, theta),
                    color=c, label=f"{s_cm:g} cm")
    for b in ("UHF", "S", "Ka", "D"):
        fb = bands.freq_hz(b) / 1e9
        ax.axvline(fb, color=MUTED, ls=":", lw=0.8)
        ax.text(fb, 1.03, b, ha="center", va="bottom")
    ax.set_xlabel("Frequency (GHz)"); ax.set_ylabel(r"Coherent reflection $\rho_s$")
    ax.set_ylim(0, 1.12)
    ax.legend(title=r"RMS height $\sigma_h$", loc="lower left")
    save(fig, "specularCp_Site01_final_adj_5mpp_surf.png", COL, 2.6)


def fig_traverse():
    from scipy.io import loadmat
    m = loadmat(f"{REPO}/matlab/site04_traj_S.mat")
    t = m["Times_s"].ravel(); g = m["GainMagnitude_dB"].ravel(); los = m["LOS"].ravel().astype(bool)
    pl = m["FSPLDirect_dB"].ravel() - g
    snr = 23 + 12 - pl - (-174 + 10 * np.log10(20e6) + 5)       # same budget as run_nrtdl_demo.m
    se = np.minimum(np.log2(1 + 10 ** (snr / 10)), 7.4)
    fig, axes = plt.subplots(3, 1, sharex=True, constrained_layout=True)
    axes[0].plot(t, g, color="#2a78d6"); axes[0].plot(t[~los], g[~los], "v", color="#e34948", ms=6)
    axes[0].set_ylabel("Tap gain\n(dB)")
    axes[1].plot(t, snr, color="#2a78d6"); axes[1].set_ylabel("Uplink\nSNR (dB)")
    axes[2].plot(t, se, color="#2a78d6"); axes[2].set_ylabel("SE\n(b/s/Hz)")
    axes[2].set_xlabel("Time (s)")
    for ax, lab in zip(axes, "abc"):
        ax.text(0.02, 0.05, f"({lab})", transform=ax.transAxes, va="bottom")
    save(fig, "site04_traj_S_trace.png", COL, 4.2)


def fig_bler():
    rows = {}
    for line in open(os.environ.get("BLER_LOG", "/tmp/matlab_regen.log")):
        mm = re.match(r"(.+?)\s+SNR\s+([+-][\d.]+) dB: BLER ([\d.]+), tput ([\d.]+) Mbps", line.strip())
        if mm:
            rows.setdefault(mm.group(1).strip(), []).append(tuple(float(x) for x in mm.group(2, 3, 4)))
    lab = {"Lunar LOS (2-ray, flat)": ("Lunar LOS", "#2a78d6", "o"),
           "Lunar NLOS (2-edge, 200 ns)": ("Lunar NLOS", "#eb6834", "s"),
           "Terrestrial TDL-C 300 ns": ("TDL-C 300 ns", "#6b6b6b", "^")}
    fig, (a1, a2) = plt.subplots(2, 1, sharex=True, constrained_layout=True)
    for k, v in rows.items():
        v = np.array(v); name, c, mk = lab[k]
        a1.semilogy(v[:, 0], np.maximum(v[:, 1], 1e-3), marker=mk, color=c, label=name, ms=5)
        a2.plot(v[:, 0], v[:, 2], marker=mk, color=c, label=name, ms=5)
    a1.set_ylabel("BLER"); a1.set_ylim(1e-3, 1.5); a1.legend(loc="lower left")
    a2.set_ylabel("Throughput\n(Mbps)"); a2.set_xlabel("SNR (dB)")
    a1.text(0.98, 0.95, "(a)", transform=a1.transAxes, ha="right", va="top")
    a2.text(0.02, 0.95, "(b)", transform=a2.transAxes, va="top")
    save(fig, "pusch_bler_lunar_vs_terrestrial.png", COL, 4.2)


def fig_amc():
    per = np.loadtxt(f"{REPO}/matlab/amc_per_mcs.csv", delimiter=",")
    env = np.loadtxt(f"{REPO}/matlab/amc_throughput_curve.csv", delimiter=",")
    fig, ax = plt.subplots(constrained_layout=True)
    for j in range(1, per.shape[1]):
        ax.plot(per[:, 0], per[:, j], color="#b0b0b0", lw=0.9, ls="--",
                label="Individual MCS" if j == 1 else None)
    ax.plot(env[:, 0], env[:, 1], color=INK, lw=2, label="AMC envelope")
    ax.set_xlabel("SNR (dB)"); ax.set_ylabel("Throughput (Mbps)")
    ax.legend(loc="upper left")
    save(fig, "amc_throughput_curve.png", COL, 2.5)


def fig_its():
    rows = json.load(open(f"{DATA}/its/out/its_validation_rows.json"))
    sites = [("WY", "Laramie (WY)", "#2a78d6", "o"), ("ID", "Snake River (ID)", "#eb6834", "s"),
             ("WA", "Columbia (WA)", "#1baf7a", "^")]
    fig, (a1, a2) = plt.subplots(1, 2, constrained_layout=True, gridspec_kw={"width_ratios": [1, 1.1]})
    lim = (-15, 110)
    a1.fill_between(lim, [lim[0] - 10, lim[1] - 10], [lim[0] + 10, lim[1] + 10], color="#ebebeb", lw=0)
    a1.plot(lim, lim, color=MUTED, lw=1)
    for sid, name, c, mk in sites:
        sub = [r for r in rows if r["site"] == sid]
        a1.scatter([r["meas_excess_db"] for r in sub], [r["pred_excess_db"] for r in sub], s=8,
                   marker=mk, color=c, alpha=0.5, edgecolors="none", label=name)
    a1.set_xlim(lim); a1.set_ylim(lim); a1.set_aspect("equal")
    a1.set_xlabel("Measured excess loss (dB)"); a1.set_ylabel("Predicted excess loss (dB)")
    a1.set_title("(a) Terrain model")
    a1.legend(loc="upper left", markerscale=1.6, handletextpad=0.2, borderaxespad=0.1)
    groups = [(s, [r for r in rows if r["site"] == s]) for s, *_ in sites] + [("All", rows)]
    models = [("Free space", "#a3a3a3", lambda r: -r["meas_excess_db"]),
              ("Smooth sphere", "#6b6b6b", lambda r: r["smooth_excess_db"] - r["meas_excess_db"]),
              ("Terrain model", "#2b2b2b", lambda r: r["pred_excess_db"] - r["meas_excess_db"])]
    x = np.arange(len(groups)); w = 0.27
    for k, (mn, c, fn) in enumerate(models):
        a2.bar(x + (k - 1) * (w + 0.015), [np.sqrt(np.mean([fn(r) ** 2 for r in g])) for _, g in groups],
               w, color=c, label=mn, zorder=2)
    a2.set_xticks(x); a2.set_xticklabels([g for g, _ in groups])
    a2.set_ylabel("RMS error (dB)"); a2.set_title("(b) RMS error by region"); a2.set_ylim(0, 70)
    a2.grid(axis="x", visible=False)
    a2.legend(loc="upper right", handlelength=1.0, borderaxespad=0.1)
    save(fig, "its_validation.png", FULL, 3.4)


def fig_twin():
    d = f"{DATA}/twin10km"
    res = json.load(open(f"{d}/twin10km.json"))
    S = np.load(f"{d}/twin10km_S.npz"); R = np.load(f"{d}/twin10km_S_refraction.npz")
    off, step, px = float(S["margin_offset"]), int(S["step"]), float(S["px"])
    demc = S["demc"]; n = demc.shape[0]; ext = [0, n * step * px / 1e3, n * step * px / 1e3, 0]
    shade = hillshade(demc, step * px); g = S["gnb_rc"]
    fig, axes = plt.subplots(1, 4, constrained_layout=True, gridspec_kw={"width_ratios": [1, 1, 1, 1.15]})
    panels = [("(a) LunaCov", S["luna"], res["S"]["lunacov_cov"]),
              ("(b) LunaTwin", S["twin"], res["S"]["twin_cov"]),
              ("(c) Refraction on", R["twin"], res["S_refraction"]["twin_cov"])]
    im = None
    for ax, (title, m, cov) in zip(axes, panels):
        ax.imshow(shade, cmap="gray", extent=ext)
        im = ax.imshow(np.ma.masked_less_equal(m + off, 0), cmap="viridis", extent=ext, vmin=0, vmax=90,
                       alpha=0.85, interpolation="nearest")
        ax.plot(g[1] * px / 1e3, g[0] * px / 1e3, "^", color="red", ms=6, mec="white")
        ax.set_title(f"{title}\n{100 * cov:.0f}% served"); ax.set_xticks([0, 5, 10]); ax.set_yticks([0, 5, 10])
        ax.grid(False); ax.set_xlabel("East (km)")
    axes[0].set_ylabel("South (km)")
    for a in axes[1:3]:
        a.set_yticklabels([]); a.set_xticks([5, 10])
    cb = fig.colorbar(im, ax=axes[:3], orientation="horizontal", shrink=0.7, pad=0.02, aspect=40)
    cb.set_label("Link margin (dB), served links")
    ax = axes[3]; b = ["UHF", "S", "Ka"]; x = np.arange(3); w = 0.27
    ax.bar(x - w, [100 * res["los_frac"]] * 3, w, color="#a3a3a3", label="LOS set", zorder=2)
    ax.bar(x, [100 * res[k]["twin_cov"] for k in b], w, color="#2a78d6", label="LunaTwin", zorder=2)
    ax.bar(x + w, [100 * res[k]["lunacov_cov"] for k in b], w, color="#eb6834", label="LunaCov", zorder=2)
    ax.set_xticks(x); ax.set_xticklabels(b); ax.set_ylabel("Served (%)"); ax.set_ylim(0, 62)
    ax.set_title("(d) By band"); ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", handlelength=0.8, borderaxespad=0.0)
    save(fig, "twin_vs_lunacov_10km.png", FULL, 3.0)


def fig_tput():
    """Uplink throughput maps; data from the 10 km run of throughput_maps (tput_ue.npz)."""
    D = np.load(f"{DATA}/figs10/tput_ue.npz")
    dem, px, g = D["dem"], float(D["px"]), D["tx"]
    n = dem.shape[0]; km = n * px / 1e3; ext = [0, km, km, 0]
    shade = hillshade(dem, px)
    fig, axes = plt.subplots(1, 3, constrained_layout=True)
    im = None
    for k, (ax, band) in enumerate(zip(axes, ("UHF", "S", "Ka"))):
        t = D[band]; cov, med = D["stats"][k]
        ax.imshow(shade, cmap="gray", extent=ext, interpolation="bilinear")
        im = ax.imshow(np.ma.masked_less_equal(t, 0), cmap="viridis", extent=ext, vmin=0, vmax=102,
                       alpha=0.8, interpolation="nearest")
        ax.plot(g[1] * px / 1e3, g[0] * px / 1e3, "^", color="red", ms=6, mec="white")
        name = "S-band" if band == "S" else ("Ka-band" if band == "Ka" else band)
        ax.set_title(f"({'abc'[k]}) {name}\n{cov:.0f}% served, median {med:.0f} Mbps")
        ax.set_xticks([0, 5, 10] if k == 0 else [5, 10]); ax.set_yticks([0, 5, 10])
        ax.grid(False); ax.set_xlabel("East (km)")
        if k: ax.set_yticklabels([])
    axes[0].set_ylabel("South (km)")
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02, aspect=25)
    cb.set_label("Uplink throughput (Mbps)")
    save(fig, "throughput_maps_ue.png", FULL, 2.9)


BANDS = (("UHF", "UHF", 0.442), ("S", "S-band", 2.5), ("Ka", "Ka-band", 27.0))


def _margin(site):
    """10 km margin maps from paper_margin_maps_10km.py, on the stride-2 grid."""
    D = np.load(f"{DATA}/figs10/{site}_margin_10km.npz")
    dem, px, tx = D["dem"][::2, ::2], 2 * float(D["px"]), D["tx"] // 2
    maps = {b: D[b][::2, ::2] for b, *_ in BANDS}
    return dem, px, tx, maps


def _cov(m):
    f = m[np.isfinite(m)]
    return 100 * np.mean(f > 0)


def fig_cov(site, name):
    dem, px, tx, maps = _margin(site)
    km = dem.shape[0] * px / 1e3; ext = [0, km, km, 0]
    shade = hillshade(dem, px)
    fig, axes = plt.subplots(1, 3, constrained_layout=True)
    im = None
    for k, (ax, (b, lab, _)) in enumerate(zip(axes, BANDS)):
        m = maps[b]
        ax.imshow(shade, cmap="gray", extent=ext, interpolation="bilinear")
        im = ax.imshow(np.ma.masked_invalid(np.where(m > 0, m, np.nan)), cmap="viridis", extent=ext,
                       vmin=0, vmax=90, alpha=0.85, interpolation="nearest")
        ax.plot(tx[1] * px / 1e3, tx[0] * px / 1e3, "^", color="red", ms=6, mec="white")
        ax.set_title(f"({'abc'[k]}) {lab}, {_cov(m):.1f}% served")
        ax.set_xticks([0, 5, 10] if k == 0 else [5, 10]); ax.set_yticks([0, 5, 10])
        ax.grid(False); ax.set_xlabel("East (km)")
        if k: ax.set_yticklabels([])
        print(f"{site} {b}: {_cov(m):.1f}%")
    axes[0].set_ylabel("South (km)")
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02, aspect=25)
    cb.set_label("Link margin (dB)")
    save(fig, f"coverage_{site}_final_adj_5mpp_surf.png", FULL, 2.75)


def fig_cov1():
    fig_cov("Site01", "Connecting Ridge")


def fig_cov4():
    fig_cov("Site04", "Shackleton rim")


def fig_hist():
    _, _, _, maps = _margin("Site01")
    m = maps["S"]; m = m[np.isfinite(m)]
    srv, sh = np.median(m[m > 0]), np.median(m[m <= 0])
    print(f"S-band margin medians: served {srv:+.1f} dB, unserved {sh:+.1f} dB, "
          f"|m|<10 dB: {100*np.mean(np.abs(m) < 10):.1f}%")
    fig, ax = plt.subplots(constrained_layout=True)
    bins = np.arange(-200, 101, 4)
    ax.hist(m[m <= 0], bins=bins, weights=np.full((m <= 0).sum(), 100 / m.size), color="#a3a3a3",
            label="Unserved", zorder=2)
    ax.hist(m[m > 0], bins=bins, weights=np.full((m > 0).sum(), 100 / m.size), color="#2a78d6",
            label="Served", zorder=2)
    ax.axvline(0, color=INK, lw=0.8)
    for v in (srv, sh):
        ax.axvline(v, color=MUTED, lw=0.8, ls="--")
        ax.text(v + 3, 0.97, f"{v:+.0f} dB".replace("-", "\u2212"), transform=ax.get_xaxis_transform(), va="top")
    ax.set_xlabel("S-band link margin (dB)"); ax.set_ylabel("Share of tile (%)")
    ax.set_ylim(0, 1.2 * ax.get_ylim()[1]); ax.set_xlim(-160, 100); ax.legend(loc="upper left")
    save(fig, "margin_hist_Site01_final_adj_5mpp_surf.png", COL, 2.4)


def fig_band():
    """Served fraction vs band, Site01: terrain-aware model vs Friis budget (no terrain)."""
    from lunarcomms.propagation import friis
    dem, px, tx, maps = _margin("Site01")
    r, c = np.mgrid[0:dem.shape[0], 0:dem.shape[1]]
    d = np.hypot(r - tx[0], c - tx[1]) * px
    fin = np.isfinite(maps["S"])
    f = np.array([fb for *_, fb in BANDS]); terr = [_cov(maps[b]) for b, *_ in BANDS]
    fr = [100 * np.mean((53 + 2 - friis.fspl_db(np.maximum(d[fin], 1.0), fb * 1e9) + 106) > 0) for fb in f]
    fig, ax = plt.subplots(constrained_layout=True)
    ax.semilogx(f, fr, "--o", color=MUTED, label="Friis, no terrain")
    ax.semilogx(f, terr, "-o", color="#2a78d6", label="Terrain-aware")
    for x, y in zip(f, terr):
        ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 7), ha="center")
    ax.set_xticks(f); ax.set_xticklabels(["UHF\n0.442", "S\n2.5", "Ka\n27"]); ax.minorticks_off()
    ax.set_xlim(0.3, 40); ax.set_ylim(0, 108)
    ax.set_xlabel("Band and carrier frequency (GHz)"); ax.set_ylabel("Served (%)")
    ax.legend(loc="center right")
    print("Friis", fr, "terrain", terr)
    save(fig, "threeband_coverage.png", COL, 2.5)


def fig_eirp():
    J = json.load(open(f"{DATA}/figs10/eirp_curves.json"))
    e = np.array(J["eirp_dbm"])
    fig, ax = plt.subplots(constrained_layout=True)
    ax.plot(e, J["friis"], "--", color=MUTED, label="Friis, no terrain")
    styles = {"2.5": ("#2a78d6", "-"), "3.2": ("#eb6834", (0, (5, 2))), "7.0": ("#1baf7a", ":")}
    for k, v in J["terrain"].items():
        col, ls = styles[k]
        ax.plot(e, v, color=col, ls=ls, lw=1.8, label=rf"Terrain, $\varepsilon'$ = {float(k):.1f}")
    for x, t in ((23, "UE"), (53, "BTS")):
        ax.axvline(x, color=MUTED, lw=0.7, ls=":")
        ax.text(x + 1, 0.93, t, transform=ax.get_xaxis_transform(), va="top")
    ax.set_xlim(0, 80); ax.set_ylim(0, 102)
    ax.set_xlabel("EIRP (dBm)"); ax.set_ylabel("Served (%)")
    ax.legend(loc="center left", bbox_to_anchor=(0.13, 0.52), frameon=True, framealpha=1, edgecolor="none")
    save(fig, "coverage_vs_eirp.png", COL, 2.5)


FIGS = {"sites": fig_sites, "validation": fig_validation, "regolith": fig_regolith,
        "specular": fig_specular, "traverse": fig_traverse, "bler": fig_bler, "amc": fig_amc,
        "its": fig_its, "twin": fig_twin, "tput": fig_tput, "cov1": fig_cov1, "cov4": fig_cov4,
        "hist": fig_hist, "band": fig_band, "eirp": fig_eirp}

if __name__ == "__main__":
    style()
    names = list(FIGS) if sys.argv[1:] == ["all"] else sys.argv[1:]
    for nm in names:
        FIGS[nm]()

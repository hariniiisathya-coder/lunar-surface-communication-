"""
Baseline-validation figure pack — the "are we implementing the models right?"
evidence for the paper.

One 2x2 panel (figures/validation_baselines.png) validating each physics
module against an INDEPENDENT reference, not against itself:

  (a) two_ray.path_loss_db vs FSPL: breakpoint d0 = 4 h_t h_r / lambda marked,
      far-field 40 log10(d) asymptote overlaid (Rappaport 1996 eq. 3.26-3.30).
  (b) diffraction.knife_edge_loss_db (ITU-R P.526-15 eq. 14 approximation)
      vs the EXACT Fresnel-integral solution computed here from
      scipy.special.fresnel — the approximation must stay within ~0.25 dB
      over nu in [-0.78, 5] (ITU's stated accuracy band).
  (c) Fresnel reflection |Gamma_v|, |Gamma_h| vs grazing angle for regolith
      (eps' = 2.658): grazing limit -> 1, pseudo-Brewster minimum of the
      vertical polarization marked; terrestrial moist soil (eps' = 15)
      dashed for contrast.
  (d) Loss tangent vs frequency: corrected uniform baseline
      (10**(0.312 rho + f**0.069 - 3.79)) against the Siegler (2020) Table 1
      per-region values pinned in tests/test_regolith.py, with the previous
      density-less baseline dashed to show the ~3x understatement it had.

Run from the project root:  python analysis/make_validation_figures.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import fresnel as fresnel_integrals

from lunarcomms.propagation import diffraction, friis, two_ray
from lunarcomms.regolith import dielectric as di

OUT = "figures/validation_baselines.png"
H_TX, H_RX, RHO = 30.0, 2.0, 1.50
F_S = 2.5e9
C = 299792458.0


def exact_knife_edge_db(nu):
    """Exact Fresnel-Kirchhoff single knife-edge loss (dB) from the Fresnel
    integrals: F(nu) = (1+j)/2 * integral_nu^inf exp(-j pi t^2/2) dt,
    loss = -20 log10 |F|. Standard result, e.g. ITU-R P.526 §4.1."""
    nu = np.asarray(nu, dtype=float)
    S, Cc = fresnel_integrals(nu)
    mag = 0.5 * np.sqrt((1.0 - Cc - S) ** 2 + (Cc - S) ** 2)
    return -20.0 * np.log10(np.maximum(mag, 1e-12))


def panel_two_ray(ax):
    d = np.logspace(1.5, 4.3, 1200)          # 30 m .. 20 km
    pl_2r = two_ray.path_loss_db(d, H_TX, H_RX, F_S)
    pl_fs = friis.fspl_db(np.hypot(d, H_TX - H_RX), F_S)
    d0 = two_ray.breakpoint_distance(H_TX, H_RX, F_S)
    # far-field asymptote PL = 40 log d - 20 log(h_t h_r)
    asym = 40.0 * np.log10(d) - 20.0 * np.log10(H_TX * H_RX)
    ax.semilogx(d, pl_2r, lw=1.0, label="two-ray (implemented)")
    ax.semilogx(d, pl_fs, "--", lw=1.0, label="free space")
    ax.semilogx(d[d > 2 * d0], asym[d > 2 * d0], ":", lw=1.8,
                label=r"$40\log d - 20\log(h_t h_r)$ asymptote")
    ax.axvline(d0, color="gray", lw=0.8)
    ax.annotate(f"$d_0$ = {d0/1e3:.1f} km", (d0, 95), rotation=90,
                fontsize=8, ha="right")
    ax.set_xlabel("ground distance (m)")
    ax.set_ylabel("path loss (dB)")
    ax.set_title(f"(a) Two-ray vs FSPL — {H_TX:.0f} m / {H_RX:.0f} m masts, "
                 "S-band", fontsize=9)
    ax.invert_yaxis()
    ax.legend(fontsize=7)
    # numeric check: beyond 3*d0 implementation must hug the asymptote
    sel = d > 3 * d0
    err = np.max(np.abs(pl_2r[sel] - asym[sel]))
    return f"two-ray far-field vs 40logd asymptote: max |err| = {err:.2f} dB (d > 3 d0)"


def panel_knife_edge(ax):
    nu = np.linspace(-1.5, 5.0, 600)
    j_itu = diffraction.knife_edge_loss_db(nu)
    j_exact = exact_knife_edge_db(nu)
    ax.plot(nu, j_exact, lw=1.6, label="exact (Fresnel integrals)")
    ax.plot(nu, j_itu, "--", lw=1.2, label="ITU-R P.526-15 eq. 14 (implemented)")
    ax.axvline(-0.78, color="gray", lw=0.8)
    ax.annotate(r"$\nu=-0.78$", (-0.78, 18), rotation=90, fontsize=8, ha="right")
    ax.set_xlabel(r"Fresnel–Kirchhoff parameter $\nu$")
    ax.set_ylabel("diffraction loss (dB)")
    ax.set_title("(b) Knife-edge: eq. 14 approximation vs exact", fontsize=9)
    ax.legend(fontsize=7)
    sel = nu >= -0.78
    err = np.max(np.abs(j_itu[sel] - j_exact[sel]))
    return f"knife-edge eq.14 vs exact Fresnel integral: max |err| = {err:.2f} dB (nu >= -0.78)"


def panel_fresnel(ax):
    theta = np.radians(np.linspace(0.2, 90.0, 800))
    gv, gh = di.fresnel_coefficients(RHO, F_S / 1e9, theta)
    ax.plot(np.degrees(theta), np.abs(gv), lw=1.4,
            label=r"$|\Gamma_V|$ regolith ($\varepsilon'$=2.66)")
    ax.plot(np.degrees(theta), np.abs(gh), lw=1.4,
            label=r"$|\Gamma_H|$ regolith")
    # terrestrial contrast: eps'=15 (moist soil). Reuse the same code path by
    # inverting rho from eps' = 1.919**rho.
    rho_soil = np.log(15.0) / np.log(1.919)
    gv15, _ = di.fresnel_coefficients(rho_soil, F_S / 1e9, theta)
    ax.plot(np.degrees(theta), np.abs(gv15), ":", lw=1.2,
            label=r"$|\Gamma_V|$ moist soil ($\varepsilon'$=15)")
    thb = np.degrees(theta[np.argmin(np.abs(gv))])
    ax.axvline(thb, color="gray", lw=0.8)
    ax.annotate(f"pseudo-Brewster {thb:.0f}°", (thb, 0.75), rotation=90,
                fontsize=8, ha="right")
    ax.set_xlabel("grazing angle (deg)")
    ax.set_ylabel(r"$|\Gamma|$")
    ax.set_title("(c) Fresnel reflection — grazing limit and Brewster dip",
                 fontsize=9)
    ax.legend(fontsize=7)
    g0 = abs(di.fresnel_coefficients(RHO, F_S / 1e9, 1e-4)[0])
    # analytic pseudo-Brewster from the normal: tan(th_i) = sqrt(eps) ->
    # grazing angle = 90 - th_i
    thb_analytic = 90.0 - np.degrees(np.arctan(np.sqrt(di.permittivity(RHO))))
    return (f"Fresnel grazing limit |Gamma_V|(0) = {g0:.4f} (theory 1); "
            f"pseudo-Brewster {thb:.1f} deg vs analytic {thb_analytic:.1f} deg")


def panel_loss_tangent(ax):
    f = np.logspace(np.log10(0.3), np.log10(40.0), 400)
    td_new = di.loss_tangent(RHO, f)
    td_old = di.loss_tangent_ab(-3.79, 0.069, f)      # previous density-less baseline
    ax.loglog(f, td_new, lw=1.6,
              label=r"baseline $10^{0.312\rho + f^{0.069} - 3.79}$ (implemented)")
    ax.loglog(f, td_old, "--", lw=1.2, color="gray",
              label="previous baseline (no density term)")
    # Siegler Table 1 regions — exactly the (a', b') pairs and S-band values
    # pinned by tests/test_regolith.py (S20_TABLE1).
    published = {
        "Mare Seren.": (-3.351, -0.0811, 0.00378),
        "Mare Tranq.": (-3.208, -0.0422, 0.00568),
        "Farside highl.": (-3.745, 0.0663, 0.00208),
    }
    for name, (a, b, td25) in published.items():
        ax.plot(2.5, td25, "o", ms=5)
        ax.annotate(name, (2.5, td25), textcoords="offset points",
                    xytext=(6, -2), fontsize=7)
        ax.loglog(f, di.loss_tangent_ab(a, b, f), lw=0.6, alpha=0.5)
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel(r"$\tan\delta$")
    ax.set_title(r"(d) Loss tangent vs Siegler (2020) — $\rho$=1.5", fontsize=9)
    ax.legend(fontsize=6.5, loc="upper left")
    return (f"baseline tan d(2.5 GHz) = {float(di.loss_tangent(RHO, 2.5)):.5f} "
            "(Siegler full form: 0.00554)")


def main():
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8))
    checks = [
        panel_two_ray(axes[0, 0]),
        panel_knife_edge(axes[0, 1]),
        panel_fresnel(axes[1, 0]),
        panel_loss_tangent(axes[1, 1]),
    ]
    fig.suptitle("Baseline validation: implementation vs independent references",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT, dpi=170)
    print(f"saved {OUT}")
    for c in checks:
        print("  CHECK:", c)


if __name__ == "__main__":
    main()

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lunarcomms.regolith.dielectric import fresnel_coefficients, permittivity

rho, f = 1.50, 2.5  # S-band
theta_deg = np.linspace(0.01, 90, 500)
theta_rad = np.radians(theta_deg)

gv, gh = fresnel_coefficients(rho, f, theta_rad)

fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(theta_deg, np.abs(gv), lw=2, label=r"$|\Gamma_v|$ (vertical / TM)")
ax.plot(theta_deg, np.abs(gh), lw=2, label=r"$|\Gamma_h|$ (horizontal / TE)")

# the true |Gamma_v| minimum on the grazing-angle axis
imin = np.argmin(np.abs(gv))
theta_min = theta_deg[imin]
ax.axvline(theta_min, color="grey", ls=":", alpha=0.7)
ax.annotate(f"|Γ_v| min ≈ {theta_min:.1f}° grazing\n(Brewster; = 90° − 58.5°)",
            xy=(theta_min, np.abs(gv)[imin]),
            xytext=(theta_min + 8, 0.4),
            arrowprops=dict(arrowstyle="->", color="grey"), fontsize=10)

ax.set_xlabel("Grazing angle (degrees)")
ax.set_ylabel("Reflection coefficient magnitude")
ax.set_title(f"Fresnel coefficients vs grazing angle — S-band, ρ={rho} (ε'={permittivity(rho):.2f})")
ax.set_xlim(0, 90); ax.set_ylim(0, 1.05)
ax.grid(alpha=0.3)
ax.legend()
fig.savefig("fresnel_plot.png", dpi=130, bbox_inches="tight")
print(f"Saved fresnel_plot.png  (|Gamma_v| minimum at {theta_min:.2f} deg grazing)")

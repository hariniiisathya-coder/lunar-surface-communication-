import numpy as np
import matplotlib
matplotlib.use("Agg")  # render to file, no display needed
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from lunarcomms.regolith.dielectric import permittivity, loss_tangent, skin_depth_m

RHO = 1.50  # density held fixed; we sweep frequency
freqs = np.logspace(np.log10(0.4), np.log10(37), 240)   # full curve (GHz)
sweep = np.logspace(np.log10(0.4), np.log10(37), 120)   # animated marker positions

fig, ax = plt.subplots(figsize=(9, 6))
ax.loglog(freqs, loss_tangent(RHO, freqs), lw=2, color="#1f4e79", label="tan d vs f")
marker, = ax.loglog([sweep[0]], [loss_tangent(RHO, sweep[0])], "o",
                     ms=13, color="#c00000")

# mark the three named bands
for fb, name in [(0.44, "UHF"), (2.5, "S"), (27.0, "Ka")]:
    ax.axvline(fb, color="grey", ls=":", alpha=0.6)
    ax.text(fb, ax.get_ylim()[0], " " + name, color="grey", va="bottom", fontsize=9)

ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel("Loss tangent  tan d")
ax.set_title("Lunar regolith loss tangent  (rho = 1.50 g/cm3)")
ax.grid(True, which="both", alpha=0.3)
ax.legend(loc="lower right")

txt = ax.text(0.04, 0.96, "", transform=ax.transAxes, va="top", fontsize=12,
              bbox=dict(boxstyle="round", fc="white", alpha=0.9))

def frame(i):
    f = sweep[i]
    td = loss_tangent(RHO, f)
    marker.set_data([f], [td])
    txt.set_text("f = %.2f GHz\ntan d = %.5f\nskin depth = %.2f m"
                 % (f, td, skin_depth_m(RHO, f)))
    return marker, txt

anim = FuncAnimation(fig, frame, frames=len(sweep), interval=60, blit=True)
anim.save("regolith_sweep.gif", writer=PillowWriter(fps=18))
print("Saved regolith_sweep.gif")

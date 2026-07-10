import numpy as np
import matplotlib
print("matplotlib backend:", matplotlib.get_backend())
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from lunarcomms.regolith.dielectric import permittivity, loss_tangent, skin_depth_m

freqs = np.logspace(np.log10(0.4), np.log10(37), 200)  # GHz axis

rho0, f0 = 1.50, 2.5

fig, ax = plt.subplots(figsize=(9, 6))
plt.subplots_adjust(bottom=0.28)

line, = ax.loglog(freqs, loss_tangent(rho0, freqs), lw=2)
marker, = ax.loglog([f0], [loss_tangent(rho0, f0)], "ro", ms=10)

ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel("Loss tangent  tan d")
ax.set_title("Lunar regolith dielectric model (drag the sliders)")
ax.grid(True, which="both", alpha=0.3)

txt = ax.text(0.04, 0.96, "", transform=ax.transAxes, va="top", fontsize=11,
              bbox=dict(boxstyle="round", fc="white", alpha=0.85))

def readout(rho, f):
    return ("rho = %.2f g/cm3\nf = %.2f GHz\neps' = %.3f\n"
            "tan d = %.5f\nskin depth = %.2f m"
            % (rho, f, permittivity(rho), loss_tangent(rho, f), skin_depth_m(rho, f)))

txt.set_text(readout(rho0, f0))

ax_rho = plt.axes([0.15, 0.13, 0.7, 0.03])
ax_f = plt.axes([0.15, 0.07, 0.7, 0.03])
s_rho = Slider(ax_rho, "Density rho (g/cm3)", 1.0, 3.0, valinit=rho0)
s_f = Slider(ax_f, "Frequency (GHz)", 0.4, 37.0, valinit=f0)

def update(val):
    rho, f = s_rho.val, s_f.val
    line.set_ydata(loss_tangent(rho, freqs))
    marker.set_data([f], [loss_tangent(rho, f)])
    txt.set_text(readout(rho, f))
    ax.relim(); ax.autoscale_view()
    fig.canvas.draw_idle()

s_rho.on_changed(update)
s_f.on_changed(update)

plt.show()


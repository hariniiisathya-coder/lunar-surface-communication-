import numpy as np
import matplotlib
matplotlib.use("Agg")  # save to file, no display needed
import matplotlib.pyplot as plt
from lunarcomms.io.pgda import load_dem

sites = [
    ("data/dem/Site01/Site01_final_adj_5mpp_surf.tif", "Connecting Ridge (Site01)"),
    ("data/dem/Site04/Site04_final_adj_5mpp_surf.tif", "Shackleton rim (Site04)"),
]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, (path, label) in zip(axes, sites):
    data, transform, crs = load_dem(path)
    # tile is 3200 px * 5 m = 16 km per side; extent in km, centred at 0
    half_km = (data.shape[0] * abs(transform.a)) / 1000.0 / 2.0
    extent = [-half_km, half_km, -half_km, half_km]

    im = ax.imshow(data, cmap="terrain", extent=extent, origin="upper")
    ax.set_title(label)
    ax.set_xlabel("East-West (km)")
    ax.set_ylabel("North-South (km)")
    # annotate the feature at tile centre
    ax.annotate(label.split(" (")[0],
                xy=(0, 0), xytext=(0, half_km * 0.6),
                ha="center", color="black", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="black"))
    fig.colorbar(im, ax=ax, label="Elevation (m)", shrink=0.8)

fig.suptitle("PGDA-78 LOLA South Pole DEMs (5 m/pixel)", fontsize=13)
fig.tight_layout()
fig.savefig("dem_plot.png", dpi=130, bbox_inches="tight")
print("Saved dem_plot.png")


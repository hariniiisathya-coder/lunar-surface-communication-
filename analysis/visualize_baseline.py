"""
Visualise the four fidelity levels as side-by-side coverage maps + a DEM panel.
Produces baseline_visual.png. Run from the project root after the paths in
run_baseline_table.py are set (this script reuses its coverage function).

    python visualize_baseline.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pyproj
from lunarcomms.io.pgda import load_dem, sample_loss_tangent_params
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

# ---- config (match run_baseline_table.py) -------------------------------
DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
A_PATH = "Figure 11_Constant Loss Parameter_a'.txt"
B_PATH = "Figure 11_Frequency Exponent_b'.txt"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS, RHO = 53.0, 2.0, -106.0, 1.50
# -------------------------------------------------------------------------


def build_pix2lonlat(transform, crs):
    moon_geog = pyproj.CRS.from_proj4("+proj=longlat +a=1737400 +b=1737400 +no_defs")
    to_ll = pyproj.Transformer.from_crs(crs, moon_geog, always_xy=True)

    def pix2lonlat(row, col):
        x = transform.c + (col + 0.5) * transform.a + (row + 0.5) * transform.b
        y = transform.f + (col + 0.5) * transform.d + (row + 0.5) * transform.e
        lon, lat = to_ll.transform(x, y)
        return lat, lon
    return pix2lonlat


def coverage(dem, px, tx, freq_hz, model, ab_sampler=None, pix2lonlat=None):
    ny, nx = dem.shape
    margin = np.full((ny, nx), np.nan)
    need_los = model in ("deygout", "spatial")
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX) if need_los else None
    tx_elev = dem[tx] + H_TX
    frac = H_TX / (H_TX + H_RX)
    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx:
                margin[i, j] = EIRP + GRX - SENS
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            d3d = np.hypot(dh, rx_elev - tx_elev)
            if model == "friis":
                pl = float(friis.fspl_db(d3d, freq_hz))
            elif model == "tworay":
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, freq_hz, RHO))
            else:
                if los[i, j]:
                    if model == "spatial" and ab_sampler is not None:
                        sr = int(round(tx[0] + frac * (i - tx[0])))
                        sc = int(round(tx[1] + frac * (j - tx[1])))
                        lat, lon = pix2lonlat(sr, sc)
                        a, b = ab_sampler(lat, lon, A_PATH, B_PATH)
                        pl = float(two_ray.path_loss_spatial_db(dh, H_TX, H_RX, freq_hz, a, b, RHO))
                    else:
                        pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, freq_hz, RHO))
                else:
                    pl = float(friis.fspl_db(d3d, freq_hz))
                    h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                    pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, freq_hz))
            prx = friis.received_power_dbm(EIRP, pl, GRX)
            margin[i, j] = friis.link_margin_db(prx, SENS)
    return margin


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    pix2lonlat = build_pix2lonlat(transform, crs)

    def ab(lat, lon, ap, bp):
        return sample_loss_tangent_params(lat, lon, ap, bp)

    models = ["friis", "tworay", "deygout", "spatial"]
    titles = ["1. Friis (free space)", "2. Two-ray (+multipath)",
              "3. Deygout (+terrain)", "4. Spatial (+dielectric)"]
    maps = {}
    for m in models:
        maps[m] = coverage(dem, px, tx, FREQ_HZ, m, ab_sampler=ab, pix2lonlat=pix2lonlat)

    fig = plt.figure(figsize=(15, 10))
    # top-left: DEM
    ax0 = plt.subplot(2, 3, 1)
    im0 = ax0.imshow(dem, cmap="terrain")
    ax0.plot(tx[1], tx[0], "r^", ms=12, label="TX")
    ax0.set_title("Site01 DEM elevation (m)")
    ax0.legend(loc="upper right")
    plt.colorbar(im0, ax=ax0, fraction=0.046)

    # top-right: binary coverage comparison (Friis vs Deygout)
    ax_cmp = plt.subplot(2, 3, 3)
    friis_cov = maps["friis"] > 0
    dey_cov = maps["deygout"] > 0
    diff = np.full(dem.shape, np.nan)
    diff[friis_cov & dey_cov] = 2      # covered by both
    diff[friis_cov & ~dey_cov] = 1     # lost to terrain
    im_c = ax_cmp.imshow(diff, cmap="RdYlGn", vmin=0, vmax=2)
    ax_cmp.plot(tx[1], tx[0], "k^", ms=10)
    ax_cmp.set_title("Green=covered, Red=lost to terrain")

    # four margin maps
    for k, (m, t) in enumerate(zip(models, titles)):
        ax = plt.subplot(2, 3, k + 3 if k >= 1 else 4)  # placement below
    # simpler: put the 4 maps in bottom row + one extra; use a clean 2x3 grid
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    # DEM
    im = axes[0, 0].imshow(dem, cmap="terrain")
    axes[0, 0].plot(tx[1], tx[0], "r^", ms=12)
    axes[0, 0].set_title("DEM elevation (m)")
    plt.colorbar(im, ax=axes[0, 0], fraction=0.046)
    # 4 margin maps
    order = [(0, 1), (0, 2), (1, 0), (1, 1)]
    for (m, t), pos in zip(zip(models, titles), order):
        model, title = m, t
        ax = axes[pos]
        im = ax.imshow(maps[model], cmap="RdYlGn", vmin=-20, vmax=40)
        ax.plot(tx[1], tx[0], "k^", ms=9)
        cov = 100 * np.nansum(maps[model] > 0) / np.sum(np.isfinite(maps[model]))
        ax.set_title(f"{title}\n{cov:.1f}% covered")
        plt.colorbar(im, ax=ax, fraction=0.046, label="margin (dB)")
    # difference panel
    ax = axes[1, 2]
    im = ax.imshow(diff, cmap="RdYlGn", vmin=0, vmax=2)
    ax.plot(tx[1], tx[0], "k^", ms=9)
    ax.set_title("Coverage lost to terrain\n(red = Friis-covered but Deygout-shadowed)")

    plt.tight_layout()
    plt.savefig("baseline_visual.png", dpi=120, bbox_inches="tight")
    print("wrote baseline_visual.png")


if __name__ == "__main__":
    main()

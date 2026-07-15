"""
Baseline fidelity comparison (plan Table 3) for Site01.

Runs the coverage pipeline at four fidelity levels on a 2 km subset and
tabulates covered area, decomposing path loss into multipath / terrain /
dielectric contributions:

    friis    : free-space only               (upper bound)
    tworay   : + ground-reflection multipath
    deygout  : + terrain diffraction
    spatial  : + spatially-varying regolith dielectric (Siegler a'/b')

Run from the project root:
    python run_baseline_table.py
"""
import numpy as np
import pyproj
from lunarcomms.io.pgda import load_dem, sample_loss_tangent_params
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

# ---- config -------------------------------------------------------------
DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
A_PATH = "Figure 11_Constant Loss Parameter_a'.txt"
B_PATH = "Figure 11_Frequency Exponent_b'.txt"
CLIP_KM = 1.0            # ~2 km box (400x400) for development
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS = 53.0, 2.0, -106.0
RHO = 1.50
# -------------------------------------------------------------------------


def build_pix2lonlat(transform, crs):
    """Return f(row, col) -> (lat_deg, lon_deg) using the DEM CRS."""
    moon_geog = pyproj.CRS.from_proj4("+proj=longlat +a=1737400 +b=1737400 +no_defs")
    to_lonlat = pyproj.Transformer.from_crs(crs, moon_geog, always_xy=True)

    def pix2lonlat(row, col):
        x = transform.c + (col + 0.5) * transform.a + (row + 0.5) * transform.b
        y = transform.f + (col + 0.5) * transform.d + (row + 0.5) * transform.e
        lon, lat = to_lonlat.transform(x, y)
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
                        pl = float(two_ray.path_loss_spatial_db(
                            dh, H_TX, H_RX, freq_hz, a, b, RHO))
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
    print(f"DEM {dem.shape}, px={px} m, TX at {tx}, elev {dem[tx]:.1f} m\n")

    pix2lonlat = build_pix2lonlat(transform, crs)

    def ab_sampler(lat, lon, ap, bp):
        return sample_loss_tangent_params(lat, lon, ap, bp)

    print(f"{'level':10s} {'model':10s} {'covered %':>10s} {'area km2':>10s} {'d vs Friis':>12s}")
    print("-" * 56)
    base_pct = None
    for level, model in enumerate(["friis", "tworay", "deygout", "spatial"], 1):
        m = coverage(dem, px, tx, FREQ_HZ, model,
                     ab_sampler=ab_sampler, pix2lonlat=pix2lonlat)
        fin = np.isfinite(m)
        cov = 100 * np.nansum(m > 0) / fin.sum()
        km2 = np.nansum(m > 0) * px * px / 1e6
        if base_pct is None:
            base_pct = cov
        print(f"{level:<10d} {model:10s} {cov:>9.1f}% {km2:>10.3f} {cov-base_pct:>11.1f}%")


if __name__ == "__main__":
    main()

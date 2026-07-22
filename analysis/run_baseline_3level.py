"""Baseline fidelity comparison (levels 1-3, no Siegler files needed)."""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS, RHO = 53.0, 2.0, -106.0, 1.50


def coverage(dem, px, tx, freq_hz, model):
    ny, nx = dem.shape
    margin = np.full((ny, nx), np.nan)
    need_los = model == "deygout"
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX) if need_los else None
    tx_elev = dem[tx] + H_TX
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
    print(f"{'level':6s} {'model':10s} {'covered %':>10s} {'area km2':>10s} {'d vs Friis':>12s}")
    print("-" * 52)
    base = None
    for lvl, model in enumerate(["friis", "tworay", "deygout"], 1):
        m = coverage(dem, px, tx, FREQ_HZ, model)
        fin = np.isfinite(m)
        cov = 100 * np.nansum(m > 0) / fin.sum()
        km2 = np.nansum(m > 0) * px * px / 1e6
        if base is None:
            base = cov
        print(f"{lvl:<6d} {model:10s} {cov:>9.1f}% {km2:>10.3f} {cov-base:>11.1f}%")


if __name__ == "__main__":
    main()

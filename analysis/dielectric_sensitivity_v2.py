"""
Follow-up diagnostic: coverage % is a coarse (binary) metric -- it only
changes if a pixel's margin crosses 0 dB. This script looks at the
CONTINUOUS margin sensitivity to eps instead, and cross-tabulates it against
grazing angle and distance, to find out WHY the coverage% was eps-invariant
even though Check 1 showed a real tail of steep angles.

Run from project root:  python dielectric_sensitivity_v2.py
"""
import numpy as np
from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
EIRP, GRX, SENS = 53.0, 2.0, -106.0


def rho_for_eps(eps):
    return np.log(eps) / np.log(1.919)


def main():
    dem, transform, crs = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)

    rho_lo = rho_for_eps(2.5)
    rho_hi = rho_for_eps(8.0)

    rows = []  # (angle_deg, distance_m, margin_lo, margin_hi, delta)
    for i in range(ny):
        for j in range(nx):
            if (i, j) == tx or not los[i, j]:
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            angle = np.degrees(np.arctan((H_TX + H_RX) / dh))
            pl_lo = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ_HZ, rho_lo))
            pl_hi = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ_HZ, rho_hi))
            m_lo = friis.link_margin_db(friis.received_power_dbm(EIRP, pl_lo, GRX), SENS)
            m_hi = friis.link_margin_db(friis.received_power_dbm(EIRP, pl_hi, GRX), SENS)
            rows.append((angle, dh, m_lo, m_hi, m_hi - m_lo))

    rows = np.array(rows)
    angle, dist, m_lo, m_hi, delta = rows.T

    print(f"n LOS pixels analysed: {len(rows)}\n")

    print("Margin sensitivity to eps (2.5 -> 8.0), overall:")
    print(f"  max |delta margin|: {np.max(np.abs(delta)):.4f} dB")
    print(f"  mean |delta margin|: {np.mean(np.abs(delta)):.4f} dB")
    print(f"  fraction with |delta| > 0.1 dB: {100*np.mean(np.abs(delta)>0.1):.1f}%")
    print(f"  fraction with |delta| > 1.0 dB: {100*np.mean(np.abs(delta)>1.0):.1f}%\n")

    print("Margin sensitivity, split by angle:")
    for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20), (20, 90)]:
        mask = (angle >= lo) & (angle < hi)
        if mask.sum() == 0:
            continue
        print(f"  angle {lo:2d}-{hi:2d} deg (n={mask.sum():6d}): "
              f"mean|delta|={np.mean(np.abs(delta[mask])):.4f} dB, "
              f"max|delta|={np.max(np.abs(delta[mask])):.4f} dB, "
              f"mean margin(eps=2.5)={np.mean(m_lo[mask]):7.1f} dB")

    print()
    print("Pixels where eps COULD flip coverage: steep angle AND near threshold")
    near_thresh = np.abs(m_lo) < 3.0   # within 3 dB of the 0 dB boundary
    steep = angle > 10
    both = near_thresh & steep
    print(f"  near-threshold (|margin|<3dB): {near_thresh.sum()} pixels")
    print(f"  steep (angle>10deg):           {steep.sum()} pixels")
    print(f"  BOTH steep AND near-threshold: {both.sum()} pixels")
    if both.sum() > 0:
        print(f"  -> of these, max |delta margin| = {np.max(np.abs(delta[both])):.3f} dB")
        print(f"  -> pixels that actually flip sign (covered<->not) between eps=2.5 and eps=8.0:")
        flips = both & (np.sign(m_lo) != np.sign(m_hi))
        print(f"     {flips.sum()} pixels flip")


if __name__ == "__main__":
    main()

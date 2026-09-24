"""Greedy set-cover for Site01 at 10 km, INTERIOR candidate highs only
(excludes tile-boundary maxima, which are analysis-window artifacts).
Node 1 is forced to the best interior high so it matches the single-site number.
"""
import numpy as np
from scipy.ndimage import maximum_filter

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 5.0
H_RX, H_TX = 2.0, 30.0
EIRP, GRX, SENS, RHO = 53.0, 2.0, -106.0, 1.50
FREQ = 2.5e9
STRIDE = 3
MARGIN_PX = 200          # exclude highs within 1 km of any edge
MIN_SEP_PX = 500         # candidates must be >= 2.5 km apart
N_CAND = 8


def coverage_mask(dem, px, tx):
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], H_TX, H_RX)
    tx_elev = dem[tx] + H_TX
    served = np.zeros((ny, nx), dtype=bool)
    valid = np.zeros((ny, nx), dtype=bool)
    for i in range(0, ny, STRIDE):
        for j in range(0, nx, STRIDE):
            if np.isnan(dem[i, j]):
                continue
            valid[i, j] = True
            if (i, j) == tx:
                served[i, j] = True
                continue
            dh = np.hypot(i - tx[0], j - tx[1]) * px
            if dh == 0:
                continue
            rx_elev = dem[i, j] + H_RX
            d3d = np.hypot(dh, rx_elev - tx_elev)
            if los[i, j]:
                pl = float(two_ray.path_loss_db(dh, H_TX, H_RX, FREQ, RHO))
            else:
                pl = float(friis.fspl_db(d3d, FREQ))
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                pl += float(diffraction.deygout_loss_db(h, dist, H_TX, H_RX, FREQ))
            if friis.link_margin_db(friis.received_power_dbm(EIRP, pl, GRX), SENS) > 0:
                served[i, j] = True
    return served, valid


def main():
    dem, transform, _ = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    ny, nx = dem.shape
    demf = np.where(np.isnan(dem), -1e9, dem)
    mx = maximum_filter(demf, size=101)
    peaks = np.argwhere((demf == mx) & (demf > -1e8))
    peaks = [rc for rc in peaks if MARGIN_PX <= rc[0] < ny - MARGIN_PX
             and MARGIN_PX <= rc[1] < nx - MARGIN_PX]
    peaks = sorted(peaks, key=lambda rc: -demf[rc[0], rc[1]])
    # greedy min-separation dedup so candidates are spatially spread interior highs
    cand = []
    for rc in peaks:
        if all(np.hypot(rc[0]-c[0], rc[1]-c[1]) >= MIN_SEP_PX for c in cand):
            cand.append((int(rc[0]), int(rc[1])))
        if len(cand) >= N_CAND:
            break
    print(f"DEM {dem.shape}; {len(cand)} interior candidate highs:", flush=True)
    for c in cand:
        print(f"   {c}  {dem[c]:.0f} m", flush=True)

    masks, valid = [], None
    for c in cand:
        s, v = coverage_mask(dem, px, c)
        masks.append(s)
        valid = v
    tot = valid.sum()
    print("\n=== Greedy set-cover (S-band, 30 m, 10 km, interior) ===", flush=True)
    chosen, union = [], np.zeros_like(masks[0])
    for k in range(len(cand)):
        best, best_gain = None, -1
        for idx, m in enumerate(masks):
            if idx in chosen:
                continue
            gain = np.logical_or(union, m).sum() - union.sum()
            if gain > best_gain:
                best_gain, best = gain, idx
        if best is None:
            break
        chosen.append(best)
        union = np.logical_or(union, masks[best])
        print(f"  node {k+1}: {cand[best]} ({dem[cand[best]]:.0f} m) "
              f"-> union {100.0*union.sum()/tot:5.1f}%  "
              f"(this node alone {100.0*masks[best].sum()/tot:5.1f}%)", flush=True)
    print("\nDONE nodes_fixed", flush=True)


if __name__ == "__main__":
    main()

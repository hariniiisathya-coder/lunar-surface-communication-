"""Site01 design levers at the 10 km tile (clip 5.0): mast-height sweep and
greedy multi-node set-cover, S-band, matching the standardized budget.
Prints numbers for Sec. Design Levers and the abstract.
"""
import time
import numpy as np
from scipy.ndimage import maximum_filter

from lunarcomms.io.pgda import load_dem
from lunarcomms.geometry.horizon import los_mask_from_tx, extract_profile
from lunarcomms.propagation import two_ray, friis, diffraction

DEM_PATH = "data/dem/Site01/Site01_final_adj_5mpp_surf.tif"
CLIP_KM = 5.0
H_RX = 2.0
EIRP, GRX, SENS, RHO = 53.0, 2.0, -106.0, 1.50
FREQ = 2.5e9          # S-band
STRIDE_MAST = 2
STRIDE_NODE = 3       # coarser for the multi-candidate greedy


def coverage_mask(dem, px, tx, h_tx, freq_hz, stride):
    """Boolean served mask on the stride grid (True=covered)."""
    ny, nx = dem.shape
    los = los_mask_from_tx(dem, px, tx[0], tx[1], h_tx, H_RX)
    tx_elev = dem[tx] + h_tx
    served = np.zeros((ny, nx), dtype=bool)
    valid = np.zeros((ny, nx), dtype=bool)
    for i in range(0, ny, stride):
        for j in range(0, nx, stride):
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
                pl = float(two_ray.path_loss_db(dh, h_tx, H_RX, freq_hz, RHO))
            else:
                pl = float(friis.fspl_db(d3d, freq_hz))
                h, dist = extract_profile(dem, tx[0], tx[1], i, j, px)
                pl += float(diffraction.deygout_loss_db(h, dist, h_tx, H_RX, freq_hz))
            m = friis.link_margin_db(friis.received_power_dbm(EIRP, pl, GRX), SENS)
            if m > 0:
                served[i, j] = True
    return served, valid


def pct(served, valid):
    return 100.0 * served.sum() / valid.sum()


def main():
    dem, transform, _ = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    tx0 = tuple(int(v) for v in np.unravel_index(np.nanargmax(dem), dem.shape))
    print(f"DEM {dem.shape}, px {px} m, best-high TX {tx0}, elev {dem[tx0]:.1f} m\n",
          flush=True)

    # --- Mast-height sweep (S-band, best-high) ---
    print("=== Mast-height sweep (S-band, 10 km tile) ===", flush=True)
    for h in (10.0, 30.0, 50.0, 100.0):
        t0 = time.time()
        served, valid = coverage_mask(dem, px, tx0, h, FREQ, STRIDE_MAST)
        print(f"  h_tx={h:6.1f} m : {pct(served, valid):5.1f}%   ({time.time()-t0:.0f}s)",
              flush=True)

    # --- Greedy multi-node set-cover (S-band, 30 m) ---
    print("\n=== Greedy set-cover (S-band, 30 m, 10 km tile) ===", flush=True)
    # candidate high points: local maxima, well separated, top by elevation
    demf = np.where(np.isnan(dem), -1e9, dem)
    mx = maximum_filter(demf, size=201)          # ~1 km separation at 5 m
    peaks = np.argwhere((demf == mx) & (demf > -1e8))
    peaks = sorted(peaks, key=lambda rc: -demf[rc[0], rc[1]])[:8]
    cand = [tuple(int(v) for v in rc) for rc in peaks]
    print(f"  {len(cand)} candidate highs: "
          + ", ".join(f"{c}({dem[c]:.0f}m)" for c in cand), flush=True)

    masks, valid = [], None
    for c in cand:
        s, v = coverage_mask(dem, px, c, 30.0, FREQ, STRIDE_NODE)
        masks.append(s)
        valid = v
    tot = valid.sum()
    chosen, union = [], np.zeros_like(masks[0])
    for k in range(3):
        best, best_gain = None, -1
        for idx, m in enumerate(masks):
            if idx in chosen:
                continue
            gain = np.logical_or(union, m).sum() - union.sum()
            if gain > best_gain:
                best_gain, best = gain, idx
        chosen.append(best)
        union = np.logical_or(union, masks[best])
        print(f"  node {k+1}: add cand {cand[best]} -> union {100.0*union.sum()/tot:5.1f}%",
              flush=True)
    print("\nDONE site01_levers", flush=True)


if __name__ == "__main__":
    main()

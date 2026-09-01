"""
Coverage-planner analyses over a real LOLA DEM for the 12-section paper:
  Sec 8  mast-height sweep (coverage vs h_tx)
  Sec 9  multi-transmitter union coverage (set-cover step)
  Sec 10 link-margin distribution (bimodal -> handover cliffs)
  Sec 11 two-ray far-field path-loss exponent (n=4) check
Usage:
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif \
      python examples/planner_analysis_pgda.py
"""
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunarcomms import bands  # noqa: E402
from lunarcomms.coverage.link_budget import compute_coverage_map  # noqa: E402
from lunarcomms.propagation import two_ray  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEM = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
CLIP_KM = float(os.environ.get("LUNAR_CLIP_KM", "10"))
MAXPX = int(os.environ.get("LUNAR_MAXPX", "110"))
EIRP, GRX, SENS = 53.0, 0.0, -106.0


def load():
    from lunarcomms.io.pgda import load_dem
    dem, tr, _ = load_dem(DEM, clip_extent_km=CLIP_KM)
    dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
    px = abs(tr[0])
    st = max(int(np.ceil(max(dem.shape) / MAXPX)), 1)
    if st > 1:
        ny, nx = dem.shape
        dem = dem[:ny // st * st, :nx // st * st]
        dem = dem.reshape(dem.shape[0] // st, st, dem.shape[1] // st, st).mean((1, 3))
        px *= st
    return dem, px, os.path.basename(DEM)


def high_point(dem, r, c, rad=5):
    ny, nx = dem.shape
    sub = dem[max(r - rad, 0):min(r + rad, ny), max(c - rad, 0):min(c + rad, nx)]
    o = np.unravel_index(np.argmax(sub), sub.shape)
    return max(r - rad, 0) + o[0], max(c - rad, 0) + o[1]


def cov_map(dem, px, tx, h, f):
    return compute_coverage_map(dem, (px, 0, 0, 0, -px, 0), None, tx[0], tx[1],
                                h, 2.0, f, EIRP, GRX, SENS, use_envelope=True)


def main():
    dem, px, name = load()
    ny, nx = dem.shape
    F = bands.freq_hz("S")
    tx0 = high_point(dem, ny // 2, nx // 4)

    # Sec 8: mast-height sweep
    print(f"[{name}] mast-height sweep (S-band, TX on local high):")
    for h in (10, 30, 50, 100):
        c = float(np.mean(cov_map(dem, px, tx0, h, F) > 0))
        print(f"  h_tx={h:3d} m : coverage={c:.1%}")

    # Sec 9: multi-TX union coverage (greedy set-cover order)
    cand = [tx0, high_point(dem, ny // 4, 3 * nx // 4),
            high_point(dem, 3 * ny // 4, nx // 2)]
    union = np.zeros(dem.shape, bool)
    print("multi-TX union coverage (30 m masts, greedy add):")
    for i, tx in enumerate(cand, 1):
        union |= (cov_map(dem, px, tx, 30.0, F) > 0)
        print(f"  {i} node(s): union coverage={union.mean():.1%}")

    # Sec 10: link-margin distribution (bimodal)
    m = cov_map(dem, px, tx0, 30.0, F)
    fin = m[np.isfinite(m)]
    figh, axh = plt.subplots(figsize=(7, 4), constrained_layout=True)
    axh.hist(fin, bins=60, color="tab:blue", alpha=0.8)
    axh.axvline(0, color="k", ls="--", lw=1)
    axh.set_xlabel("link margin (dB)")
    axh.set_ylabel("pixels")
    axh.set_title(f"Link-margin distribution is bimodal ({name}, S)")
    figh.savefig(f"{HERE}/margin_hist_{os.path.splitext(name)[0]}.png", dpi=120)
    plt.close(figh)
    served = np.mean(fin > 0)
    print(f"margin distribution: served={served:.1%}, "
          f"median served={np.median(fin[fin > 0]):.1f} dB, "
          f"median unserved={np.median(fin[fin <= 0]):.1f} dB (cliff)")

    # Sec 11: two-ray far-field path-loss exponent
    d = np.array([3e4, 3e5])
    pl = two_ray.path_loss_db(d, 30, 2, F)
    n = (pl[1] - pl[0]) / (10 * np.log10(d[1] / d[0]))
    print(f"two-ray far-field path-loss exponent n = {n:.2f} (expect 4.0)")
    print(f"wrote margin_hist_{os.path.splitext(name)[0]}.png")


if __name__ == "__main__":
    main()

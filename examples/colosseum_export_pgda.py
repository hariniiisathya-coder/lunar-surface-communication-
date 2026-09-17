"""
Export a rover-trajectory scenario over a real LOLA DEM to a Colosseum/MCHEM
tap grid, so a lunar 5G waveform can be replayed on the emulator.

Pipeline (the original Paper-2 plan, stage 4):
  DEM -> per-waypoint sparse taps (two-ray LOS / Deygout NLOS, spatial regolith
  optional) -> quantize onto the MCHEM grid (<=4 taps, 10 ns cell, 5.11 us max)
  -> CSV that a Colosseum scenario ingests, plus a per-waypoint gain trace.

Usage:
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif \
      python examples/colosseum_export_pgda.py
"""
import csv
import os

import numpy as np

from lunarcomms import bands
from lunarcomms.export import taps

HERE = os.path.dirname(os.path.abspath(__file__))
DEM = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
BAND = os.environ.get("LUNAR_BAND", "S")
CLIP_KM = float(os.environ.get("LUNAR_CLIP_KM", "6"))
H_TX, H_RX = 30.0, 2.0


def load():
    if os.path.exists(DEM):
        from lunarcomms.io.pgda import load_dem
        dem, tr, _ = load_dem(DEM, clip_extent_km=CLIP_KM)
        dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
        return dem, abs(tr[0]), os.path.basename(DEM)
    return np.zeros((21, 400)), 5.0, "synthetic-flat"


def main():
    dem, px, name = load()
    ny, nx = dem.shape
    tx = np.unravel_index(np.argmax(dem), dem.shape)  # BTS on a local high
    # radial rover track eastward from the BTS
    cols = range(int(tx[1]) + 3, min(nx, int(tx[1]) + 3 + 300), 2)
    path = [(int(tx[0]), c) for c in cols]
    f = bands.freq_hz(BAND)
    links = taps.trajectory_taps(dem, px, int(tx[0]), int(tx[1]), path,
                                 H_TX, H_RX, f)

    out_csv = os.path.join(HERE, f"colosseum_{os.path.splitext(name)[0]}_{BAND}.csv")
    n_over = 0
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["waypoint", "dist_m", "los", "tap", "delay_ns",
                    "gain_db", "phase_rad", "fspl_direct_db"])
        for i, lk in enumerate(links):
            delays, gains = taps.to_colosseum_taps(lk)  # <=4 taps on 10 ns grid
            if len(delays) > taps.MCHEM_MAX_TAPS:
                n_over += 1
            for t, (d_s, g) in enumerate(zip(delays, gains)):
                w.writerow([i, f"{lk.meta['d_ground_m']:.1f}", int(lk.los), t,
                            f"{d_s * 1e9:.1f}",
                            f"{20 * np.log10(max(abs(g), 1e-12)):.2f}",
                            f"{np.angle(g):.4f}", f"{lk.fspl_direct_db:.2f}"])

    # compliance report
    n_taps = [len(taps.to_colosseum_taps(lk)[0]) for lk in links]
    maxdelay = max(float(taps.to_colosseum_taps(lk)[0].max()) if len(
        taps.to_colosseum_taps(lk)[0]) else 0.0 for lk in links)
    ok = "OK" if max(n_taps) <= taps.MCHEM_MAX_TAPS else "TRUNCATED"
    grid_ns = taps.MCHEM_TAP_RESOLUTION_S * 1e9
    max_us = taps.MCHEM_MAX_DELAY_S * 1e6
    print(f"{name} @ {BAND} ({f/1e9:g} GHz): {len(links)} waypoints -> {out_csv}")
    print(f"  taps/link: min={min(n_taps)} max={max(n_taps)} "
          f"(MCHEM limit {taps.MCHEM_MAX_TAPS}) -> {ok}")
    print(f"  max excess delay {maxdelay*1e9:.1f} ns "
          f"(grid {grid_ns:g} ns, max {max_us:g} us)")
    print(f"  links exceeding tap budget: {n_over}")

    # also drop a MATLAB .mat for nrTDLChannel replay of the same track
    taps.save_nrtdl_mat(links, os.path.join(
        HERE, f"colosseum_{os.path.splitext(name)[0]}_{BAND}.mat"),
        collapse_below_s=taps.MCHEM_TAP_RESOLUTION_S)


if __name__ == "__main__":
    main()

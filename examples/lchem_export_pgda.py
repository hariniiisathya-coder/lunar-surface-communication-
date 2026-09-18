"""
Export a rover-trajectory scenario over a real LOLA DEM to LCHEM MT-012 frames.

Pipeline: DEM -> per-waypoint sparse taps (LunaCov) -> LCHEM complex-16 PDP
(<=16 complex taps, 10 ns ticks, Q1.15, shiftright split) -> JSON of CIR frames
(feed live with lchem.stream_lchem once the X410 endpoint is up).

Usage:
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif \
      python examples/lchem_export_pgda.py
"""
import os

import numpy as np

from lunarcomms import bands
from lunarcomms.export import lchem, taps

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
    tx = np.unravel_index(np.argmax(dem), dem.shape)   # gNB on a local high
    cols = range(int(tx[1]) + 3, min(nx, int(tx[1]) + 3 + 300), 2)
    path = [(int(tx[0]), c) for c in cols]
    f = bands.freq_hz(BAND)

    links = taps.trajectory_taps(dem, px, int(tx[0]), int(tx[1]), path,
                                 H_TX, H_RX, f)
    frames = [[p] for p in lchem.trajectory_to_lchem(links, lchem.GNB, lchem.UE1)]

    out = os.path.join(HERE, f"lchem_{os.path.splitext(name)[0]}_{BAND}.json")
    lchem.save_lchem_json(frames, out)

    n_taps = [len(fr[0]["coeffs"]) for fr in frames]
    max_tick = max(max(fr[0]["delays_10ns"]) for fr in frames)
    shifts = [fr[0]["shiftright_bits"] for fr in frames]
    print(f"{name} @ {BAND} ({f/1e9:g} GHz): {len(frames)} CIR frames -> {out}")
    print(f"  taps/link: min={min(n_taps)} max={max(n_taps)} "
          f"(LCHEM complex-16 limit 16) -> {'OK' if max(n_taps) <= 16 else 'OVER'}")
    print(f"  max delay {max_tick} ticks = {max_tick*10:.0f} ns "
          f"(span limit 16.67 us = 1667 ticks)")
    print(f"  shiftright range {min(shifts)}-{max(shifts)} bits (0-12)")
    print("  stream live: lchem.stream_lchem(frames, host=<X410>, "
          "port=5006, period_s=waypoint_spacing/rover_speed)")


if __name__ == "__main__":
    main()

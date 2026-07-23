"""
Export a lunar surface channel to MATLAB nrTDLChannel format and independently
cross-check it in Python (verification layer 5: recompute in a second path).

Run:  python examples/export_channel_demo.py
Produces:  channel_traj.mat  (for examples/verify_nrtdl.m in MATLAB)
Prints a PASS/FAIL cross-check that the exported taps reproduce
two_ray.path_loss_db along the trajectory to < 0.05 dB.
"""
import os

import numpy as np

from lunarcomms.export import taps
from lunarcomms.propagation import two_ray

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "channel_traj.mat")

# Flat DEM so the ground-truth is exactly two_ray.path_loss_db.
FLAT = np.zeros((21, 400))
PX = 5.0
TX = (10, 10)
H_TX, H_RX, F = 30.0, 2.0, 2.5e9

# Rover trajectory: straight radial run away from the BTS.
path = [(10, c) for c in range(30, 400, 2)]
links = taps.trajectory_taps(FLAT, PX, TX[0], TX[1], path, H_TX, H_RX, F)

# Export for MATLAB nrTDLChannel (DelayProfile='Custom'), collapsed to the
# 10 ns MCHEM grid so each LOS link is a single complex tap.
taps.save_nrtdl_mat(links, OUT, collapse_below_s=taps.MCHEM_TAP_RESOLUTION_S)

# Append the Python two_ray reference PL per waypoint so MATLAB can do a
# quantitative loop-closure comparison (not just "does it load").
from scipy.io import loadmat, savemat  # noqa: E402
ref_pl = np.array([[float(two_ray.path_loss_db(lk.meta["d_ground_m"],
                                               H_TX, H_RX, F))] for lk in links])
mat = loadmat(OUT)
mat["TwoRayPL_dB"] = ref_pl
savemat(OUT, {k: v for k, v in mat.items() if not k.startswith("__")})
print(f"wrote {OUT}")

# ---- Python-side independent cross-check ------------------------------------
worst = 0.0
for lk in links:
    d = lk.meta["d_ground_m"]
    clk = lk.collapsed(taps.MCHEM_TAP_RESOLUTION_S)
    pl_tap = lk.fspl_direct_db - 20.0 * np.log10(abs(clk.gains[0]))
    pl_ref = float(two_ray.path_loss_db(d, H_TX, H_RX, F))
    worst = max(worst, abs(pl_tap - pl_ref))
print(f"max |exported tap PL - two_ray.path_loss_db| = {worst:.4f} dB")
print("PASS (< 0.05 dB)" if worst < 0.05 else "FAIL")

# What MATLAB should reproduce: total path loss per waypoint =
# FSPLDirect_dB - GainMagnitude_dB (the .mat carries both).
print("\nMATLAB check: load channel_traj.mat; total PL = FSPLDirect_dB - "
      "GainMagnitude_dB must match two_ray (see examples/verify_nrtdl.m).")

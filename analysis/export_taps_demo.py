"""
End-to-end demo export: DEM -> rover-trajectory taps -> MATLAB .mat.

Builds a straight rover traverse across the committed Site04 tile (passing
through the rough western zone so the trace shows both two-ray oscillation
and NLOS diffraction dips), computes the tap set at every waypoint with
lunarcomms.export.taps, and writes matlab/site04_traj_S.mat with everything
matlab/run_nrtdl_demo.m needs:

    PathDelays        (N x T)  s, excess delay, direct ray = 0
    AveragePathGains  (N x T)  dB relative to the free-space direct ray
    InitialPhasesRad  (N x T)
    FSPLDirect_dB     (N x 1)  absolute anchor per waypoint
    LOS               (N x 1)  1 = line of sight
    GainMagnitude_dB  (N x 1)  collapsed complex-sum tap (the fading trace)
    CarrierHz         scalar
    Times_s           (N x 1)  waypoint time at ROVER_SPEED_MPS
    PathRowCol        (N x 2)  DEM pixel indices
    PixelSize_m       scalar

Run from the project root:  python analysis/export_taps_demo.py
"""
import numpy as np
from scipy.io import loadmat, savemat

from lunarcomms.export import taps
from lunarcomms.io.pgda import load_dem

DEM_PATH = "data/dem/Site04/Site04_final_adj_5mpp_surf.tif"
CLIP_KM = 1.0
FREQ_HZ = 2.5e9
H_TX, H_RX = 30.0, 2.0
ROVER_SPEED_MPS = 1.0          # EVA walking pace
STEP_PX = 2                    # waypoint every 10 m on the 5 m grid
OUT = "matlab/site04_traj_S.mat"


def main():
    dem, transform, _ = load_dem(DEM_PATH, clip_extent_km=CLIP_KM)
    px = abs(transform.a)
    ny, nx = dem.shape
    tx = (ny // 2, nx // 2)

    # West -> east traverse through the tile centre row: crosses the rough
    # western zone (NLOS dips) and the smooth centre (two-ray oscillation).
    cols = list(range(int(0.05 * nx), int(0.95 * nx), STEP_PX))
    path = [(tx[0], c) for c in cols if (tx[0], c) != tx]

    print(f"DEM {ny}x{nx} @ {px:.0f} m, mast {tx}, {len(path)} waypoints")
    links = taps.trajectory_taps(dem, px, tx[0], tx[1], path,
                                 H_TX, H_RX, FREQ_HZ)
    taps.save_nrtdl_mat(links, OUT,
                        collapse_below_s=taps.MCHEM_TAP_RESOLUTION_S)

    # Append demo metadata (timestamps, waypoint pixels) to the same .mat.
    extra = loadmat(OUT)
    dist_m = np.array([abs(c - path[0][1]) * px for (_, c) in path])
    extra["Times_s"] = (dist_m / ROVER_SPEED_MPS).reshape(-1, 1)
    extra["PathRowCol"] = np.array(path, dtype=float)
    extra["PixelSize_m"] = px
    extra = {k: v for k, v in extra.items() if not k.startswith("__")}
    savemat(OUT, extra)

    n_los = sum(lk.los for lk in links)
    mags = [20 * np.log10(max(abs(np.sum(lk.collapsed().gains)), 1e-12))
            for lk in links]
    print(f"saved {OUT}: {len(links)} waypoints, LOS {n_los}/{len(links)}, "
          f"collapsed gain {min(mags):.1f}..{max(mags):.1f} dB rel. free space")


if __name__ == "__main__":
    main()

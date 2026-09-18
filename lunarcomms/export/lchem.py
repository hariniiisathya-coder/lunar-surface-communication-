"""
LCHEM export: turn LunaCov link channels into LCHEM MT-012 PDP frames.

LCHEM is an open-source RFNoC hardware-in-the-loop channel emulator on a USRP
X410 (245.76 MS/s, 4.069 ns sample). It ingests Channel Impulse Responses over
a ZeroMQ MT-012 message, not a CSV: each frame is a list of PDPs, one per link,
``(src_node, dst_node, delays_10ns, coeffs)`` with delays in 10 ns ticks and
Q1.15 complex/real coefficients. See the LCHEM user guide, sec. 3-4.

Two hardware variants:
  * complex-16 (NOC 0x5F1A0004): <=16 complex taps, tau_max ~16.67 us
    (Dmax=4096), Doppler via host Q1.15 rotation. RECOMMENDED for LunaCov --
    the two-ray/Deygout taps are complex and sparse (1-3 taps), so they fit
    with room to spare and keep the interference phase.
  * real-32   (NOC 0x5F1A0003): <=32 real taps, tau_max ~8.33 us, no Doppler.
    Magnitude-only; loses inter-tap phase. Provided for completeness.

Scale split (Q1.15 gives ~42 dB usable; a surface FSPL is ~120 dB). The tap
COEFFICIENTS carry the channel SHAPE (relative to the free-space direct ray);
the ABSOLUTE attenuation ``fspl_direct_db`` is applied by the analog chain:
coarse in 6.02 dB steps via the MT-011 shiftright block (0-12 bits), residual
via the launch-time RF tx/rx gains. :func:`to_lchem_pdp` returns all three so
the operator sets them consistently.
"""

from __future__ import annotations

import numpy as np

from .taps import LinkTaps, to_colosseum_taps

#: MT-012 wire delay tick (the guide expresses delays in 10 ns ticks even
#: though the FPGA places taps on the finer 4.069 ns sample grid).
LCHEM_TICK_S = 10e-9

#: Variant limits (max non-zero taps, max delay span).
LCHEM_VARIANTS = {
    "complex16": {"max_taps": 16, "max_delay_s": 16.67e-6, "complex": True,
                  "noc_id": "0x5F1A0004"},
    "real32": {"max_taps": 32, "max_delay_s": 8.33e-6, "complex": False,
               "noc_id": "0x5F1A0003"},
}

_Q115 = 1 << 15                 # Q1.15 full scale
_SHIFT_DB_PER_BIT = 20.0 * np.log10(2.0)   # 6.0206 dB
_SHIFT_MAX_BITS = 12
_Q115_USABLE_DB = 42.0          # per the guide (quantization-limited)

#: Default node-id map (LCHEM: 0=gNB, 2/4/6=UE1..3).
GNB, UE1, UE2, UE3 = 0, 2, 4, 6


def _q115(x: np.ndarray) -> np.ndarray:
    """Round to Q1.15 and clip to [-1, 1). Returns float in [-1, 1)."""
    q = np.round(np.asarray(x, dtype=float) * _Q115)
    q = np.clip(q, -_Q115, _Q115 - 1)
    return q / _Q115


def to_lchem_pdp(
    link: LinkTaps,
    src_node: int = GNB,
    dst_node: int = UE1,
    mode: str = "complex16",
    headroom: float = 0.9,
):
    """One LCHEM PDP for a single Tx->Rx link.

    Returns a dict with the MT-012 payload fields plus the analog-scale split:
      src_node, dst_node : LCHEM node ids.
      delays_10ns        : list[int], excess delays in 10 ns ticks (tap 0 = 0).
      coeffs             : list[complex] (or list[float] for real32), Q1.15,
                           |coeff| < 1, peak scaled to ``headroom``.
      shiftright_bits    : int in [0, 12], coarse attenuation (6.02 dB/bit).
      rf_residual_db     : float, remaining attenuation for the RF tx/rx gains.
      norm_gain_db, fspl_direct_db, mode : bookkeeping.

    The three scale terms reconstruct the absolute channel:
        applied_atten_db = shiftright_bits*6.02 + rf_residual_db
                         = fspl_direct_db - norm_gain_db.
    """
    if mode not in LCHEM_VARIANTS:
        raise ValueError(f"mode must be one of {list(LCHEM_VARIANTS)}")
    v = LCHEM_VARIANTS[mode]

    delays_s, gains = to_colosseum_taps(
        link, n_taps=v["max_taps"], tap_resolution_s=LCHEM_TICK_S,
        max_delay_s=v["max_delay_s"])
    if len(delays_s) == 0:                      # unreachable link: single null tap
        delays_s, gains = np.array([0.0]), np.array([0.0 + 0.0j])

    delays_10ns = [int(round(d / LCHEM_TICK_S)) for d in delays_s]

    if v["complex"]:
        c = np.asarray(gains, dtype=complex)
    else:
        # real32: align the peak tap to real-positive, keep the real projection.
        k = int(np.argmax(np.abs(gains)))
        phase = np.exp(-1j * np.angle(gains[k])) if abs(gains[k]) > 0 else 1.0
        c = np.real(np.asarray(gains, dtype=complex) * phase)

    peak = float(np.max(np.abs(c))) if np.max(np.abs(c)) > 0 else 1.0
    scale = headroom / peak
    norm_gain_db = 20.0 * np.log10(1.0 / scale)      # + = we scaled coeffs down
    c = _q115(np.real(c * scale)) + (
        1j * _q115(np.imag(c * scale)) if v["complex"] else 0.0)

    atten_db = float(link.fspl_direct_db) - norm_gain_db
    shift_bits = int(np.clip(round(atten_db / _SHIFT_DB_PER_BIT),
                             0, _SHIFT_MAX_BITS))
    rf_residual_db = atten_db - shift_bits * _SHIFT_DB_PER_BIT

    coeffs = ([complex(x) for x in c] if v["complex"]
              else [float(np.real(x)) for x in c])
    return {
        "src_node": int(src_node), "dst_node": int(dst_node),
        "delays_10ns": delays_10ns, "coeffs": coeffs,
        "shiftright_bits": shift_bits, "rf_residual_db": float(rf_residual_db),
        "norm_gain_db": float(norm_gain_db),
        "fspl_direct_db": float(link.fspl_direct_db),
        "mode": mode, "noc_id": v["noc_id"],
    }


def trajectory_to_lchem(
    links: list[LinkTaps],
    src_node: int = GNB,
    dst_node: int = UE1,
    mode: str = "complex16",
    headroom: float = 0.9,
) -> list[dict]:
    """PDP frames along a rover trajectory (one per waypoint).

    Streaming these in sequence realizes the time-varying channel: the tap
    phase evolves waypoint-to-waypoint, i.e. the physical Doppler a moving UE
    sees. Pace the stream at ``waypoint_spacing / rover_speed``; the complex-16
    variant additionally rotates taps between updates (f_d ~250-500 Hz).
    """
    return [to_lchem_pdp(lk, src_node, dst_node, mode, headroom) for lk in links]


def pdps_to_mt012_tuples(pdps: list[dict]) -> list[tuple]:
    """Pack PDP dicts into the ``(src, dst, delays_10ns, coeffs)`` tuples that
    the LCHEM host ``mt_encoders.encode_mt012`` expects (guide sec. 4.2)."""
    return [(p["src_node"], p["dst_node"], p["delays_10ns"], p["coeffs"])
            for p in pdps]


def stream_lchem(
    frames: list[list[dict]],
    host: str = "127.0.0.1",
    port: int = 5006,
    taps_per_filter: int = 16,
    period_s: float | None = None,
):
    """Push CIR frames to a live LCHEM over ZeroMQ MT-012.

    ``frames`` is a list of frames; each frame is a list of per-link PDP dicts
    (from :func:`to_lchem_pdp`). Requires the LCHEM host library (``zmq`` and
    ``mt_encoders`` from github.com/wineslab/lchem_deploy). If ``period_s`` is
    set, frames are paced at that interval (the rover update cadence).
    """
    import time

    import zmq
    from mt_encoders import encode_mt012  # from lchem_deploy host tree

    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.connect(f"tcp://{host}:{port}")
    for i, frame in enumerate(frames, 1):
        msg = encode_mt012(pdps_to_mt012_tuples(frame),
                           taps_per_filter=taps_per_filter, msg_counter=i,
                           tap_app_sec=int(time.time() * 1e9))
        sock.send(msg)
        if period_s:
            time.sleep(period_s)
    sock.close()


def save_lchem_json(frames: list[list[dict]], path: str) -> None:
    """Offline dump of CIR frames (for feeding LCHEM without a live link)."""
    import json

    def enc(p: dict) -> dict:
        return {**p, "coeffs": [[float(np.real(x)), float(np.imag(x))]
                                for x in p["coeffs"]]}

    with open(path, "w") as f:
        json.dump([[enc(p) for p in frame] for frame in frames], f, indent=2)


__all__ = [
    "LCHEM_TICK_S", "LCHEM_VARIANTS", "GNB", "UE1", "UE2", "UE3",
    "to_lchem_pdp", "trajectory_to_lchem", "pdps_to_mt012_tuples",
    "stream_lchem", "save_lchem_json",
]

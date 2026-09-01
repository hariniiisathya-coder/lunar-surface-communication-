"""
Per-ray departure/arrival elevation angles for the two-ray geometry, and the
resulting antenna-pattern weight on the ground-reflected ray.

The two rays of the two-ray model leave the transmitter (and reach the
receiver) at different elevations:

  direct ray    Tx->Rx :  el = atan2(h_rx - h_tx, d)     (near-horizontal)
  direct ray    Rx<-Tx :  el = atan2(h_tx - h_rx, d)
  reflected ray Tx->gnd:  el = -atan2(h_tx + h_rx, d)     (steeper, downward)
  reflected ray gnd->Rx:  el = -atan2(h_tx + h_rx, d)

Both rays share the link azimuth plane (az = 0), so the pattern
differentiates them purely in elevation. The reflected ray therefore picks up
a real gain ratio relative to the direct ray:

  w = [g_tx(refl) g_rx(refl)] / [g_tx(dir) g_rx(dir)]

which multiplies the reflected term of  E/E_direct = 1 + w * Gamma (r1/r2)
e^{-j k dr}. With isotropic patterns w == 1 and the model is unchanged.
"""

from __future__ import annotations

import numpy as np

from .patterns import Isotropic, Pattern

_RAD2DEG = 180.0 / np.pi


def ray_elevations_deg(distance_m, h_tx_m: float, h_rx_m: float):
    """(el_tx_dir, el_rx_dir, el_tx_refl, el_rx_refl) in degrees.

    Elevation is measured from the local horizon, +up. Arrays broadcast over
    ``distance_m``.
    """
    d = np.asarray(distance_m, dtype=float)
    el_tx_dir = np.arctan2(h_rx_m - h_tx_m, d) * _RAD2DEG
    el_rx_dir = np.arctan2(h_tx_m - h_rx_m, d) * _RAD2DEG
    el_refl = -np.arctan2(h_tx_m + h_rx_m, d) * _RAD2DEG
    return el_tx_dir, el_rx_dir, el_refl, el_refl


def ray_pattern_weight(
    el_tx_ref_deg,
    el_rx_ref_deg,
    el_tx_ray_deg,
    el_rx_ray_deg,
    tx_pattern: Pattern | None = None,
    rx_pattern: Pattern | None = None,
):
    """Field-gain of a ray relative to a reference direction.

    Returns
        w = [g_tx(ray) g_rx(ray)] / [g_tx(ref) g_rx(ref)]
    where ``ref`` is the direction the GLOBAL link budget (EIRP / Rx gain)
    already accounts for -- the geometric direct direction -- and ``ray`` is
    where this particular ray actually leaves the Tx / reaches the Rx. All
    angles are elevations in degrees, azimuth is the shared link plane (0).
    Isotropic patterns give w == 1, so callers passing no pattern are
    unchanged. Array-safe.
    """
    if tx_pattern is None:
        tx_pattern = Isotropic()
    if rx_pattern is None:
        rx_pattern = Isotropic()
    zt = np.zeros_like(np.asarray(el_tx_ref_deg, dtype=float))
    zr = np.zeros_like(np.asarray(el_rx_ref_deg, dtype=float))
    g_ref = tx_pattern.field_gain(zt, el_tx_ref_deg) * rx_pattern.field_gain(
        zr, el_rx_ref_deg
    )
    g_ray = tx_pattern.field_gain(zt, el_tx_ray_deg) * rx_pattern.field_gain(
        zr, el_rx_ray_deg
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(g_ref > 0, g_ray / g_ref, 0.0)
    return float(w) if np.ndim(w) == 0 else w


def reflected_ray_weight(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    tx_pattern: Pattern | None = None,
    rx_pattern: Pattern | None = None,
):
    """Real field-gain weight on the two-ray reflected ray vs the direct ray.

    Returns 1.0 (scalar or array matching ``distance_m``) when both patterns
    are isotropic/omni -- so callers that pass no pattern are unchanged.
    """
    el_tx_dir, el_rx_dir, el_tx_refl, el_rx_refl = ray_elevations_deg(
        distance_m, h_tx_m, h_rx_m
    )
    return ray_pattern_weight(
        el_tx_dir, el_rx_dir, el_tx_refl, el_rx_refl, tx_pattern, rx_pattern
    )


__all__ = ["ray_elevations_deg", "reflected_ray_weight", "ray_pattern_weight"]

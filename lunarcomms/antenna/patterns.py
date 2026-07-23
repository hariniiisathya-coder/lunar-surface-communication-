"""
Antenna radiation patterns for the lunar surface link.

Why this module exists
----------------------
The rest of the pipeline treats antennas as scalar EIRP / Rx gain (isotropic):
the two-ray field sum in :mod:`lunarcomms.propagation.two_ray` weights the
direct and ground-reflected rays EQUALLY, regardless of the antenna's shape.
That is the isotropic-source assumption shared by Edwards (2023, Friis-only)
and RadioLunaDiff (2025, Sionna-RT with one-hot pixel sources). On a real mast
the direct ray (near-horizontal) and the ground reflection (steeper, toward the
surface) leave the antenna at DIFFERENT elevation angles, so a directional or
downtilted element weights them differently -- changing null depth, breakpoint
behaviour and, over terrain, coverage.

Convention
----------
A :class:`Pattern` maps a direction ``(az_deg, el_deg)`` to a *field* gain
(linear amplitude, so it multiplies the ray field directly; power gain is its
square). Directions are antenna-local:

  * ``el_deg`` -- elevation above the local horizon (+up). A horizon-pointing
    mast has boresight at ``el_deg = 0``.
  * ``az_deg`` -- azimuth from boresight (0 = toward the link partner).

For the two-ray geometry both rays share the link azimuth plane (az = 0), so
the direct/reflected differentiation is purely in elevation -- but the azimuth
cut is implemented too, for completeness and for off-axis coverage use.

The directional element is the 3GPP TR 38.901 Table 7.3-1 single-element
pattern (8 dBi max, 65 deg HPBW in both cuts, 30 dB front-to-back, SLA_V = 30),
i.e. the pattern MATLAB ``phased.NRAntennaElement`` implements, so a channel
exported here stays consistent with a 5G-Toolbox downstream.

Polarization note
-----------------
These are scalar (co-pol) power/field patterns; polarization is handled
separately by the Fresnel reflection coefficient in
:mod:`lunarcomms.regolith.dielectric` (currently V-pol). The pattern multiplies
the ray amplitude; it does not rotate the polarization state.

Source
------
3GPP TR 38.901 v17.0.0, Table 7.3-1 ("Radiation power pattern of a single
antenna element"). ETSI TR 138 901.
"""

from __future__ import annotations

import numpy as np


class Pattern:
    """Base class: a direction -> field-gain (linear amplitude) map."""

    def gain_dbi(self, az_deg, el_deg):
        """Power gain in dBi at (az_deg, el_deg). Override in subclasses."""
        raise NotImplementedError

    def field_gain(self, az_deg, el_deg):
        """Linear FIELD amplitude gain = 10 ** (gain_dbi / 20).

        This is what multiplies a ray's complex field; the corresponding power
        gain is ``field_gain ** 2``.
        """
        return 10.0 ** (np.asarray(self.gain_dbi(az_deg, el_deg), float) / 20.0)


class Isotropic(Pattern):
    """Isotropic (or uniform-gain) element: constant ``gain_dbi`` everywhere.

    The default (0 dBi) reproduces the pipeline's current behaviour exactly:
    field gain 1 in every direction, so the two-ray ratio g(refl)/g(dir) = 1.
    """

    def __init__(self, gain_dbi: float = 0.0):
        self._g = float(gain_dbi)

    def gain_dbi(self, az_deg, el_deg):
        shape = np.broadcast(np.asarray(az_deg, float),
                             np.asarray(el_deg, float)).shape
        return np.full(shape, self._g) if shape else self._g


class ThreeGPP38901Element(Pattern):
    """3GPP TR 38.901 Table 7.3-1 single-element pattern.

    Vertical cut   A_EV(theta') = -min[ 12 (theta'/HPBW_el)^2 , SLA_V ]
    Horizontal cut A_EH(az)     = -min[ 12 (az/HPBW_az)^2     , A_max  ]
    Combined       A''          = -min[ -(A_EV + A_EH)        , A_max  ]
    Gain (dBi)     = G_max + A''

    where theta' is the elevation offset from the (possibly downtilted)
    boresight: theta' = el_deg + downtilt_deg. All defaults are the 38.901
    macro values (HPBW = 65 deg, SLA_V = A_max = 30 dB, G_max = 8 dBi).

    Sanity (Table 7.3-1, defaults, boresight at el=0):
      * gain_dbi(0, 0)      =  8.0  dBi   (boresight)
      * gain_dbi(0, +-32.5) =  5.0  dBi   (-3 dB, half of 65 deg HPBW)
      * gain_dbi(180, 0)    = -22.0 dBi   (30 dB front-to-back)
    """

    def __init__(
        self,
        max_gain_dbi: float = 8.0,
        hpbw_az_deg: float = 65.0,
        hpbw_el_deg: float = 65.0,
        sla_v_db: float = 30.0,
        a_max_db: float = 30.0,
        downtilt_deg: float = 0.0,
    ):
        self.max_gain_dbi = float(max_gain_dbi)
        self.hpbw_az_deg = float(hpbw_az_deg)
        self.hpbw_el_deg = float(hpbw_el_deg)
        self.sla_v_db = float(sla_v_db)
        self.a_max_db = float(a_max_db)
        self.downtilt_deg = float(downtilt_deg)

    def gain_dbi(self, az_deg, el_deg):
        az = np.asarray(az_deg, dtype=float)
        el = np.asarray(el_deg, dtype=float)
        # Wrap azimuth to [-180, 180] so the horizontal cut is symmetric and
        # the back lobe (|az| -> 180) is reached correctly.
        az = (az + 180.0) % 360.0 - 180.0
        # Elevation offset from the downtilted boresight. Positive downtilt
        # points boresight below the horizon, so a ray at el=0 sits at offset
        # +downtilt from boresight.
        theta_v = el + self.downtilt_deg
        a_ev = -np.minimum(12.0 * (theta_v / self.hpbw_el_deg) ** 2, self.sla_v_db)
        a_eh = -np.minimum(12.0 * (az / self.hpbw_az_deg) ** 2, self.a_max_db)
        a_pp = -np.minimum(-(a_ev + a_eh), self.a_max_db)
        out = self.max_gain_dbi + a_pp
        return float(out) if out.ndim == 0 else out


__all__ = ["Pattern", "Isotropic", "ThreeGPP38901Element"]

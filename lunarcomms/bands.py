"""
Canonical carrier-frequency ladder for the lunar surface study.

The scaffold anchored its two-ray/coverage targets at UHF (442 MHz), S (2.5
GHz) and Ka (27 GHz) -- the LunaNet / 3GPP-for-Moon bands. This module names
those and EXTENDS the ladder upward to FR2 (28 GHz) and D-band (140 GHz) so the
pipeline can address Paper 2's counterintuitive high-band question: on Earth
140 GHz is crushed by >120 dB/km of atmospheric absorption, but the Moon has no
atmosphere (0 dB/km), so the only high-band penalties are aperture, pointing
and SURFACE ROUGHNESS (see lunarcomms.propagation.roughness) -- which the
pipeline now quantifies. That turns "the Moon may be a better home for sub-THz
links" from a hand-wave into a computed curve.

Frequencies are the representative carrier of each band; use them directly as
the ``freq_hz`` argument throughout the pipeline.

References
----------
LunaNet Interoperability Specification / SFCG 32-2R5 (UHF & S surface bands).
3GPP TR 38.101-2 (FR2 28 GHz). IEEE 802.15.3d / D-band (110-170 GHz).
"""

from __future__ import annotations

#: name -> representative carrier frequency in Hz
BANDS: dict[str, float] = {
    "UHF": 0.442e9,   # 442 MHz  -- LunaNet Forward/Return proximity link
    "S": 2.5e9,       # 2.5 GHz  -- scaffold S-band reference
    "Ka": 27.0e9,     # 27 GHz   -- Ka relay / high-rate surface
    "FR2": 28.0e9,    # 28 GHz   -- 3GPP FR2 (mmWave 5G NR)
    "D": 140.0e9,     # 140 GHz  -- D-band sub-THz (IEEE 802.15.3d)
}

#: the extended ladder, ascending, for sweeps/figures
LADDER_HZ: tuple[float, ...] = tuple(sorted(BANDS.values()))


def freq_hz(name: str) -> float:
    """Carrier (Hz) for a band name, e.g. ``freq_hz("D") == 140e9``."""
    try:
        return BANDS[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown band {name!r}; known: {sorted(BANDS)}"
        ) from exc


__all__ = ["BANDS", "LADDER_HZ", "freq_hz"]

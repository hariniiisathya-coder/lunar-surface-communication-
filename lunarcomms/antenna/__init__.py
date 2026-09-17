"""
lunarcomms.antenna
==================
Antenna radiation patterns and their per-ray weighting for the two-ray
lunar-surface link. Closes the isotropic-source assumption shared by Edwards
(2023) and RadioLunaDiff (2025): the direct and ground-reflected rays leave the
antenna at different elevations, so a directional/downtilted element weights
them differently.

Public API
----------
Isotropic(gain_dbi=0.0)              : uniform-gain reference (default = today)
ThreeGPP38901Element(downtilt_deg=0) : 3GPP TR 38.901 Table 7.3-1 element
reflected_ray_weight(...)            : field-gain weight on the reflected ray
ray_elevations_deg(...)              : per-ray departure/arrival elevations

Usage
-----
>>> from lunarcomms.antenna import ThreeGPP38901Element
>>> from lunarcomms.propagation import two_ray
>>> bts = ThreeGPP38901Element(downtilt_deg=6.0)
>>> pl = two_ray.path_loss_db(5000, 30, 2, 2.5e9, tx_pattern=bts)
"""

from .geometry import ray_elevations_deg, ray_pattern_weight, reflected_ray_weight
from .patterns import Isotropic, Pattern, ThreeGPP38901Element

__all__ = [
    "Pattern",
    "Isotropic",
    "ThreeGPP38901Element",
    "reflected_ray_weight",
    "ray_pattern_weight",
    "ray_elevations_deg",
]

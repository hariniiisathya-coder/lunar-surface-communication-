"""
lunarcomms.regolith
===================
Dielectric properties of lunar regolith for RF propagation.

The *first* module to implement. All other propagation modules import from here
to set the reflection coefficients and skin depth at the reflection point.

Public API
----------
dielectric.permittivity(rho)
dielectric.loss_tangent(rho, freq_ghz)
dielectric.complex_permittivity(rho, freq_ghz)
dielectric.skin_depth_m(rho, freq_ghz)
dielectric.fresnel_coefficients(rho, freq_ghz, theta_rad)
"""

from .dielectric import (
    complex_permittivity,
    fresnel_coefficients,
    loss_tangent,
    permittivity,
    skin_depth_m,
)

__all__ = [
    "permittivity",
    "loss_tangent",
    "complex_permittivity",
    "skin_depth_m",
    "fresnel_coefficients",
]

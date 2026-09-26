"""
Regolith radio material for the LunarTwin Sionna scene.

Where BostonTwin assigns concrete/glass BSDFs to buildings, the Moon needs one
material: regolith. We derive its Sionna radio-material parameters (relative
permittivity and conductivity) from the same primary-source physics LunaCov
uses -- Olhoeft permittivity and the Siegler loss tangent -- so the two CIR
sources share a dielectric. Pure computation; the Sionna object is built lazily.
"""

from __future__ import annotations

from ..regolith import dielectric

_EPS0 = 8.8541878128e-12   # F/m


def regolith_material_params(rho: float, freq_ghz: float,
                             a_prime: float | None = None,
                             b_prime: float | None = None) -> dict:
    """Sionna radio-material parameters for regolith at a carrier.

    Returns ``{relative_permittivity, conductivity, tan_delta}``. Conductivity
    follows from the loss tangent: sigma = 2*pi*f*eps0*eps'*tan_delta. Pass
    ``a_prime, b_prime`` (from the Siegler maps at the site lat/lon) for the
    spatial loss tangent; omit them for the uniform baseline.
    """
    eps_r = float(dielectric.permittivity(rho))
    if a_prime is not None and b_prime is not None:
        td = float(dielectric.loss_tangent_ab(a_prime, b_prime, freq_ghz))
    else:
        td = float(dielectric.loss_tangent(rho, freq_ghz))
    f_hz = float(freq_ghz) * 1e9
    sigma = 2.0 * 3.141592653589793 * f_hz * _EPS0 * eps_r * td
    return {"relative_permittivity": eps_r, "conductivity": sigma,
            "tan_delta": td}


def build_radio_material(name: str, rho: float, freq_ghz: float,
                         a_prime: float | None = None,
                         b_prime: float | None = None):
    """Construct a Sionna ``RadioMaterial`` (lazy import; needs Sionna RT)."""
    from sionna.rt import RadioMaterial
    p = regolith_material_params(rho, freq_ghz, a_prime, b_prime)
    return RadioMaterial(name,
                         relative_permittivity=p["relative_permittivity"],
                         conductivity=p["conductivity"])


__all__ = ["regolith_material_params", "build_radio_material"]

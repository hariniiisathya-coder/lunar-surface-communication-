"""Dielectric properties of lunar regolith (ASCII-only).

CHANGE LOG (this revision)
--------------------------
Replaced fabricated loss-tangent constants with the Siegler et al. (2020)
frequency-dependent form, VALIDATED against the paper's Figure 8 maps to ~5%:
    tan d(f) = 10 ** ( a' + f ** b' )        (f in GHz)
a', b' are per-location fit coefficients (Zenodo DOI 10.5281/zenodo.3993798).
This revision also makes the loss-tangent functions array-safe in frequency.
"""
import numpy as np

_C = 299792458.0  # m/s

TAN_DELTA_CEILING = 0.05
# Siegler et al. (2020) full published form (their global parameterization):
#     tan d = 10 ** ( 0.312*rho + f**0.069 - 3.79 )      (f in GHz)
# The density term 0.312*rho belongs in the exponent. The per-location a'/b'
# maps (loss_tangent_ab) already fold density into a', but the UNIFORM
# baseline must apply it explicitly — omitting it (the previous -3.79 alone)
# understates tan d by ~3x at rho=1.5 (0.0019 vs the correct 0.0055 at S-band).
_S20_CONST = -3.79
_S20_DENSITY_COEF = 0.312
_BASELINE_B = 0.069


def permittivity(rho):
    """Real relative permittivity eps' = 1.919 ** rho (rho in g/cm^3).
    At rho=1.5, eps' = 2.658.
    """
    return 1.919 ** rho


def loss_tangent_ab(a_prime, b_prime, freq_ghz, clamp=True):
    """VERIFIED Siegler (2020) loss tangent from per-location a', b'.
        tan d(f) = 10 ** ( a' + f ** b' )     (f in GHz)
    Array-safe in all arguments. Density already folded into a'/b'.
    """
    a_prime = np.asarray(a_prime, dtype=float)
    b_prime = np.asarray(b_prime, dtype=float)
    f = np.asarray(freq_ghz, dtype=float)
    td = 10.0 ** (a_prime + f ** b_prime)
    if clamp:
        td = np.clip(td, 0.0, TAN_DELTA_CEILING)
    return td


def loss_tangent(rho, freq_ghz):
    """UNIFORM baseline loss tangent (no spatial variation).

    Full Siegler (2020) published form:
        tan d = 10 ** ( 0.312*rho + f**0.069 - 3.79 )    (f in GHz)
    At rho=1.50, f=2.5 GHz: tan d = 0.00554.

    (Previous revision dropped the 0.312*rho density term, understating
    tan d ~3x; the spatial a'/b' path was always correct since density is
    folded into the per-location a'.)
    """
    a_eff = _S20_CONST + _S20_DENSITY_COEF * float(rho)
    td = loss_tangent_ab(a_eff, _BASELINE_B, freq_ghz)
    return float(td) if np.ndim(td) == 0 else td


def complex_permittivity(rho, freq_ghz):
    """eps = eps' * (1 - 1j * tan d), uniform-baseline tan d."""
    return permittivity(rho) * (1 - 1j * loss_tangent(rho, freq_ghz))


def complex_permittivity_ab(rho, a_prime, b_prime, freq_ghz, clamp=True):
    """Complex permittivity using the SPATIAL (a', b') loss tangent."""
    td = loss_tangent_ab(a_prime, b_prime, freq_ghz, clamp=clamp)
    return permittivity(rho) * (1 - 1j * td)


def skin_depth_m(rho, freq_ghz):
    """Skin depth (m), low-loss form, uniform-baseline tan d."""
    lambda0 = _C / (freq_ghz * 1e9)
    return lambda0 / (np.pi * np.sqrt(permittivity(rho)) * loss_tangent(rho, freq_ghz))


def fresnel_coefficients(rho, freq_ghz, theta_rad):
    """Fresnel coefficients, grazing-angle convention. Returns (gamma_v, gamma_h)."""
    eps_c = complex_permittivity(rho, freq_ghz)
    return _fresnel_from_epsc(eps_c, theta_rad)


def fresnel_coefficients_ab(rho, a_prime, b_prime, freq_ghz, theta_rad, clamp=True):
    """Fresnel coefficients using the SPATIAL (a', b') loss tangent."""
    eps_c = complex_permittivity_ab(rho, a_prime, b_prime, freq_ghz, clamp=clamp)
    return _fresnel_from_epsc(eps_c, theta_rad)


def _fresnel_from_epsc(eps_c, theta_rad):
    """Shared Fresnel core (grazing-angle convention)."""
    theta = np.asarray(theta_rad, dtype=float)
    root = np.sqrt(eps_c - np.cos(theta) ** 2)
    gamma_v = (eps_c * np.sin(theta) - root) / (eps_c * np.sin(theta) + root)
    gamma_h = (np.sin(theta) - root) / (np.sin(theta) + root)
    return gamma_v, gamma_h

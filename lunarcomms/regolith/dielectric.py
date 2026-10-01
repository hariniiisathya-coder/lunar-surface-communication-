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


# Siegler et al. (2020), Eq. 9: the depth-integrated loss tangent is
# tan d = 10**(0.5473 + a' + f**b'). The a', b' values of their Table 1 exclude
# the 0.5473 density term; the gridded a' maps (Zenodo 10.5281/zenodo.3993798,
# "Figure 11") already include it.
S20_EQ9_DENSITY_TERM = 0.5473


def loss_tangent_ab(a_prime, b_prime, freq_ghz, clamp=True):
    """Siegler (2020) loss tangent from per-location a', b'.
        tan d(f) = 10 ** ( a' + f ** b' )     (f in GHz)
    Array-safe in all arguments. Use with the gridded a', b' maps, whose a'
    already contains the density term; for the Table 1 values of the paper use
    loss_tangent_table1().
    """
    a_prime = np.asarray(a_prime, dtype=float)
    b_prime = np.asarray(b_prime, dtype=float)
    f = np.asarray(freq_ghz, dtype=float)
    td = 10.0 ** (a_prime + f ** b_prime)
    if clamp:
        td = np.clip(td, 0.0, TAN_DELTA_CEILING)
    return td


def loss_tangent_table1(a_prime, b_prime, freq_ghz):
    """Loss tangent from a Siegler (2020) Table 1 pair (Eq. 9):
        tan d = 10 ** ( 0.5473 + a' + f ** b' ).
    """
    return loss_tangent_ab(S20_EQ9_DENSITY_TERM + np.asarray(a_prime, dtype=float),
                           b_prime, freq_ghz)


def loss_tangent(rho, freq_ghz):
    """UNIFORM baseline loss tangent (no spatial variation).

    Full Siegler (2020) published form:
        tan d = 10 ** ( 0.312*rho + f**0.069 - 3.79 )    (f in GHz)
    At rho=1.50, f=2.5 GHz: tan d = 0.00554.

    This is the generalized highland form of Siegler et al. (2020), Eq. 11
    with Table 3 (a = -3.79, b = 0.069, density coefficient 0.312).
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

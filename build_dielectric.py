content = '''"""Dielectric properties of lunar regolith (ASCII-only)."""

import numpy as np


def permittivity(rho):
    """eps' = 1.919 ** rho."""
    return 1.919 ** rho


def loss_tangent(rho, freq_ghz):
    """tan d = 10 ** (0.312*rho - 2.636) * freq_ghz ** 0.278."""
    return 10 ** (0.312 * rho - 2.636) * freq_ghz ** 0.278


def complex_permittivity(rho, freq_ghz):
    """eps = eps' * (1 - 1j * tan d)."""
    return permittivity(rho) * (1 - 1j * loss_tangent(rho, freq_ghz))


def skin_depth_m(rho, freq_ghz):
    """delta_s = lambda0 / (pi * sqrt(eps') * tan d), lambda0 = c/f."""
    c = 299792458.0
    lambda0 = c / (freq_ghz * 1e9)
    return lambda0 / (np.pi * np.sqrt(permittivity(rho)) * loss_tangent(rho, freq_ghz))


def fresnel_coefficients(rho, freq_ghz, theta_rad):
    """Fresnel coefficients, grazing-angle convention. Returns (gamma_v, gamma_h)."""
    eps_c = complex_permittivity(rho, freq_ghz)
    theta = np.asarray(theta_rad, dtype=float)
    root = np.sqrt(eps_c - np.cos(theta) ** 2)
    gamma_v = (eps_c * np.sin(theta) - root) / (eps_c * np.sin(theta) + root)
    gamma_h = (np.sin(theta) - root) / (np.sin(theta) + root)
    return gamma_v, gamma_h
'''

with open("lunarcomms/regolith/dielectric.py", "w") as f:
    f.write(content)

print("Wrote dielectric.py with", content.count("def "), "functions")

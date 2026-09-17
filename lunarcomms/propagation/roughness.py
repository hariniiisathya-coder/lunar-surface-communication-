"""
Surface-roughness reduction of the coherent (specular) ground reflection.

Why this matters on the Moon
----------------------------
The two-ray model uses a smooth-surface Fresnel coefficient Gamma at every
band. That is fine at UHF/S, but as frequency rises the wavelength shrinks
toward the RMS height of the regolith and the reflection stops being specular:
energy scatters diffusely and the COHERENT reflection that drives the two-ray
interference weakens. Multiplying Gamma by a roughness factor rho_s in [0, 1]
captures this -- at high band the reflected ray dies, the two-ray nulls fill
in, and the link reverts toward pure free space (the direct ray). This is what
lets the pipeline answer Paper 2's "specular-vs-diffuse transition frequency"
map and its "does mmWave/sub-THz wide-area coverage become viable without an
atmosphere?" question.

Definitions (grazing-angle convention, theta measured from the surface)
-----------------------------------------------------------------------
Rayleigh roughness parameter:
    Ra = 4*pi*sigma_h*sin(theta) / lambda
The surface is "smooth" (Rayleigh criterion) when Ra < pi/2, i.e.
    sigma_h < lambda / (8 sin theta).

Coherent (specular) field-reflection reduction factor:
  * Ament / Beckmann-Spizzichino (default):
        rho_s = exp( -Ra^2 / 2 )  =  exp( -8 (pi sigma_h sin theta / lambda)^2 )
  * Miller-Brown-Vegh modification (fills the over-attenuation at large Ra,
    accounting for the mean scattered field):
        rho_s = exp( -Ra^2/2 ) * I0( Ra^2/2 )   ( = scipy i0e(Ra^2/2) )

Sources
-------
Ament, W. S. (1953). Toward a theory of reflection by a rough surface.
    Proc. IRE 41(1), 142-146.
Beckmann, P., & Spizzichino, A. (1963). The Scattering of Electromagnetic
    Waves from Rough Surfaces. Pergamon, ch. 5 (specular reduction exp(-g/2),
    g = (4 pi sigma_h cos theta_i / lambda)^2).
Miller, A. R., Brown, R. M., & Vegh, E. (1984). New derivation for the
    rough-surface reflection coefficient and for the distribution of
    sea-wave elevations. IEE Proc. H 131(2), 114-116.
"""

from __future__ import annotations

import numpy as np

_C = 299792458.0  # m/s


def rayleigh_parameter(sigma_h_m, freq_hz, grazing_angle_rad):
    """Rayleigh roughness parameter Ra = 4*pi*sigma_h*sin(theta)/lambda.

    Ra < pi/2 => surface behaves as smooth at this band and grazing angle.
    Array-safe in every argument.
    """
    lam = _C / np.asarray(freq_hz, dtype=float)
    theta = np.asarray(grazing_angle_rad, dtype=float)
    return 4.0 * np.pi * np.asarray(sigma_h_m, float) * np.sin(theta) / lam


def is_smooth(sigma_h_m, freq_hz, grazing_angle_rad):
    """Boolean Rayleigh criterion (Ra < pi/2)."""
    return rayleigh_parameter(sigma_h_m, freq_hz, grazing_angle_rad) < (np.pi / 2.0)


def specular_factor(sigma_h_m, freq_hz, grazing_angle_rad, model="ament"):
    """Coherent specular field-reflection reduction rho_s in [0, 1].

    Multiply the smooth-surface Fresnel Gamma by this to obtain the coherent
    reflected-field amplitude. ``model``:
      * "ament"        -> exp(-Ra^2/2)               (Beckmann-Spizzichino)
      * "miller-brown" -> exp(-Ra^2/2) I0(Ra^2/2)    (Miller-Brown-Vegh)

    Array-safe. sigma_h_m = 0 gives rho_s = 1 (perfectly smooth), so passing a
    roughness of zero (the default everywhere else) leaves the model unchanged.
    """
    ra = rayleigh_parameter(sigma_h_m, freq_hz, grazing_angle_rad)
    x = ra ** 2 / 2.0
    if model == "ament":
        out = np.exp(-x)
    elif model == "miller-brown":
        from scipy.special import i0e  # i0e(x) == exp(-x) * I0(x), overflow-safe
        out = i0e(x)
    else:
        raise ValueError(f"unknown roughness model {model!r}")
    return float(out) if np.ndim(out) == 0 else out


__all__ = ["rayleigh_parameter", "is_smooth", "specular_factor"]

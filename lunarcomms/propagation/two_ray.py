"""
Two-ray ground reflection model over a flat lunar regolith surface.
**Student 1 (S1) — Week 3 implementation task.**

Implemented against the scaffold's stated test targets. Physics: coherent sum
of the direct and ground-reflected rays; beyond the breakpoint the reflected
ray (grazing, Gamma -> -1) partially cancels the direct ray, giving a 1/d^4
(40 log d) far-field rolloff.

Source: Rappaport (1996), Wireless Communications, ch. 3, eqs. 3.26-3.30.
"""
import numpy as np

from ..regolith.dielectric import fresnel_coefficients, fresnel_coefficients_ab
from .friis import fspl_db

_C = 2.998e8  # m/s   (kept as in the scaffold for target consistency)


def breakpoint_distance(h_tx_m: float, h_rx_m: float, freq_hz: float) -> float:
    """Critical (breakpoint) distance d0 = 4 * h_tx * h_rx / lambda.

    Equivalently d0 = 4 * h_tx * h_rx * f / c.

    Targets (h_tx=30, h_rx=2):
        breakpoint_distance(30, 2, 0.442e9) ~   354 m
        breakpoint_distance(30, 2, 2.5e9)   ~ 2 000 m
        breakpoint_distance(30, 2, 8.4e9)   ~ 6 720 m
        breakpoint_distance(30, 2, 27.0e9)  ~ 21 600 m
    """
    return 4.0 * h_tx_m * h_rx_m * float(freq_hz) / _C


def _geometry(distance_m, h_tx_m, h_rx_m):
    """Return (r1 direct, r2 reflected, theta grazing-angle-from-surface rad)."""
    d = np.asarray(distance_m, dtype=float)
    r1 = np.sqrt(d ** 2 + (h_tx_m - h_rx_m) ** 2)
    r2 = np.sqrt(d ** 2 + (h_tx_m + h_rx_m) ** 2)
    theta = np.arctan2((h_tx_m + h_rx_m), d)   # grazing angle from the ground
    return r1, r2, theta


def _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma):
    """Core two-ray path loss (dB) given a reflection coefficient Gamma.

    Field ratio relative to the direct ray:
        E/E_direct = 1 + Gamma * (r1/r2) * exp(-j k (r2 - r1))
    PL = FSPL(r1, f) - 20 log10 |E/E_direct|.
    """
    d = np.asarray(distance_m, dtype=float)
    lam = _C / float(freq_hz)
    k = 2.0 * np.pi / lam
    r1, r2, _ = _geometry(d, h_tx_m, h_rx_m)

    field_ratio = 1.0 + gamma * (r1 / r2) * np.exp(-1j * k * (r2 - r1))
    mag = np.maximum(np.abs(field_ratio), 1e-6)  # guard perfect nulls
    return fspl_db(r1, freq_hz) - 20.0 * np.log10(mag)


def path_loss_db(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    rho: float = 1.50,
):
    """Two-ray path loss over flat lunar regolith (dB, positive = loss).

    Uniform-dielectric baseline: uses the vertical-pol Fresnel coefficient from
    the uniform-baseline loss tangent (dielectric.fresnel_coefficients).

    Targets (h_tx=30, h_rx=2, f=2.5 GHz):
        d=100 m  : ~ fspl_db(100, 2.5e9)   +/- ~6 dB (oscillations)
        d=10 km  : ~ fspl_db(10 km,2.5e9)  + ~20 dB (1/d^4 penalty)
    """
    freq_ghz = float(freq_hz) / 1e9         # dielectric fns take GHz
    _, _, theta = _geometry(distance_m, h_tx_m, h_rx_m)
    gamma_v, _ = fresnel_coefficients(rho, freq_ghz, theta)   # V-pol
    return _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma_v)


def path_loss_spatial_db(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    a_prime_map,
    b_prime_map,
    rho: float = 1.50,
    reflection_point_fraction: float = 0.5,
):
    """Two-ray path loss with spatially varying loss tangent (Siegler 2020).

    CORRECTED FORMULA: the loss tangent uses the VALIDATED Siegler form
        tan d = 10 ** ( a' + f**b' )
    (NOT the a'*f**b' written in the original scaffold TODO, which is wrong and
    yields negative loss tangents). This is applied inside
    dielectric.fresnel_coefficients_ab via loss_tangent_ab, with clamping.

    a_prime_map, b_prime_map : a' and b' at the specular reflection point for
        each distance (scalars or arrays broadcastable to distance_m). Obtain
        from lunarcomms.io.pgda.sample_loss_tangent_params(lat, lon, ...) after
        mapping each distance to its specular reflection point.

    rho : bulk density for eps' = 1.919**rho (real part only; default 1.50 ->
          eps'=2.658). Density is NOT re-applied to tan d (already in a'/b').
    """
    freq_ghz = float(freq_hz) / 1e9
    _, _, theta = _geometry(distance_m, h_tx_m, h_rx_m)
    gamma_v, _ = fresnel_coefficients_ab(
        rho, a_prime_map, b_prime_map, freq_ghz, theta, clamp=True
    )
    return _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma_v)


def specular_reflection_point_fraction(h_tx_m: float, h_rx_m: float) -> float:
    """Flat-Earth specular point location as a fraction of d from the TX:
        x_spec / d = h_tx / (h_tx + h_rx).

    For h_tx=30, h_rx=2 -> 0.9375 (i.e. 4.69 km along a 5 km path). Use this to
    pick the lat/lon at which to sample a'/b' for path_loss_spatial_db.
    """
    return h_tx_m / (h_tx_m + h_rx_m)

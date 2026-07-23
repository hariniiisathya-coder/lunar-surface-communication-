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


def _reflected_ray_weight(distance_m, h_tx_m, h_rx_m, tx_pattern, rx_pattern):
    """Antenna field-gain weight on the reflected ray (1.0 if no patterns).

    Kept as a thin wrapper so the isotropic default costs nothing and imports
    the antenna package only when a pattern is actually supplied.
    """
    if tx_pattern is None and rx_pattern is None:
        return 1.0
    from ..antenna.geometry import reflected_ray_weight
    return reflected_ray_weight(distance_m, h_tx_m, h_rx_m,
                                tx_pattern, rx_pattern)


def _apply_roughness(gamma, sigma_h_m, freq_hz, theta, model):
    """Scale Gamma by the coherent-reflection roughness factor (1.0 if smooth)."""
    if not sigma_h_m:
        return gamma
    from .roughness import specular_factor
    return gamma * specular_factor(sigma_h_m, freq_hz, theta, model=model)


def _select_pol(gamma_v, gamma_h, pol):
    """Pick the Fresnel coefficient for polarization ``pol`` ('v' or 'h')."""
    p = str(pol).lower()
    if p in ("v", "vertical"):
        return gamma_v
    if p in ("h", "horizontal"):
        return gamma_h
    raise ValueError(f"pol must be 'v' or 'h', got {pol!r}")


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


def _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma,
                           refl_weight=1.0):
    """Core two-ray path loss (dB) given a reflection coefficient Gamma.

    Field ratio relative to the direct ray:
        E/E_direct = 1 + w * Gamma * (r1/r2) * exp(-j k (r2 - r1))
    PL = FSPL(r1, f) - 20 log10 |E/E_direct|.

    ``refl_weight`` (w) is the antenna-pattern field-gain of the reflected ray
    relative to the direct ray (see lunarcomms.antenna.reflected_ray_weight);
    w == 1 (the default) reproduces the isotropic two-ray model exactly. Note
    the direct ray stays the 0 dB reference, so PL here is loss relative to the
    direct-ray antenna gain, which the link budget applies once, globally.
    """
    d = np.asarray(distance_m, dtype=float)
    lam = _C / float(freq_hz)
    k = 2.0 * np.pi / lam
    r1, r2, _ = _geometry(d, h_tx_m, h_rx_m)

    field_ratio = 1.0 + refl_weight * gamma * (r1 / r2) * np.exp(-1j * k * (r2 - r1))
    mag = np.maximum(np.abs(field_ratio), 1e-6)  # guard perfect nulls
    return fspl_db(r1, freq_hz) - 20.0 * np.log10(mag)


def path_loss_db(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    rho: float = 1.50,
    tx_pattern=None,
    rx_pattern=None,
    sigma_h_m: float = 0.0,
    roughness_model: str = "ament",
    pol: str = "v",
):
    """Two-ray path loss over flat lunar regolith (dB, positive = loss).

    Uniform-dielectric baseline: uses the Fresnel coefficient from the
    uniform-baseline loss tangent (dielectric.fresnel_coefficients).

    pol : polarization of the reflection, ``"v"`` (vertical, default) or
        ``"h"`` (horizontal). Near grazing (long links) both -> -1 and the
        choice is immaterial; at steeper angles (short range / high masts)
        V-pol shows a Brewster magnitude dip and phase flip that H-pol does
        not. Default "v" reproduces the scaffold targets. Surface UE
        (rover/EVA) links are often omni/circular -- pick "h" or average the
        two for a circular co-pol estimate.

    tx_pattern, rx_pattern : optional lunarcomms.antenna.Pattern instances. When
        supplied, the ground-reflected ray is weighted by the antenna field gain
        at its (steeper, downward) departure/arrival elevations relative to the
        near-horizontal direct ray -- so a directional or downtilted mast alters
        the null depth. Default (None) == isotropic == unchanged behaviour.

    sigma_h_m : RMS surface height (m) for the coherent-reflection roughness
        reduction (roughness.specular_factor). Default 0 = perfectly smooth =
        unchanged. As frequency rises past lambda/(8 sin theta) the reflected
        ray decoheres, the two-ray nulls fill in, and PL reverts toward FSPL.

    Targets (h_tx=30, h_rx=2, f=2.5 GHz):
        d=100 m  : ~ fspl_db(100, 2.5e9)   +/- ~6 dB (oscillations)
        d=10 km  : ~ fspl_db(10 km,2.5e9)  + ~20 dB (1/d^4 penalty)
    """
    freq_ghz = float(freq_hz) / 1e9         # dielectric fns take GHz
    _, _, theta = _geometry(distance_m, h_tx_m, h_rx_m)
    gv, gh = fresnel_coefficients(rho, freq_ghz, theta)
    gamma = _select_pol(gv, gh, pol)
    gamma = _apply_roughness(gamma, sigma_h_m, freq_hz, theta, roughness_model)
    w = _reflected_ray_weight(distance_m, h_tx_m, h_rx_m, tx_pattern, rx_pattern)
    return _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma,
                                  refl_weight=w)


def path_loss_spatial_db(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    a_prime_map,
    b_prime_map,
    rho: float = 1.50,
    reflection_point_fraction: float = 0.5,
    tx_pattern=None,
    rx_pattern=None,
    sigma_h_m: float = 0.0,
    roughness_model: str = "ament",
    pol: str = "v",
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
    gv, gh = fresnel_coefficients_ab(
        rho, a_prime_map, b_prime_map, freq_ghz, theta, clamp=True
    )
    gamma = _select_pol(gv, gh, pol)
    gamma = _apply_roughness(gamma, sigma_h_m, freq_hz, theta, roughness_model)
    w = _reflected_ray_weight(distance_m, h_tx_m, h_rx_m, tx_pattern, rx_pattern)
    return _two_ray_pl_from_gamma(distance_m, h_tx_m, h_rx_m, freq_hz, gamma,
                                  refl_weight=w)


def path_loss_envelope_db(
    distance_m,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
):
    """Two-ray LOCAL-MEAN (envelope) path loss (dB) -- the dual-slope
    breakpoint model without the fast interference oscillation.

    path_loss_db() returns the exact coherent direct+reflected sum, whose deep
    nulls are FAST FADING: on a coverage MAP sampled at the DEM pixel they
    alias into concentric-ring moire (the null spacing falls below the pixel,
    especially at high frequency). For coverage/throughput maps use this
    envelope; keep the exact oscillation for tap/trajectory export
    (lunarcomms.export.taps), where a moving rover genuinely resolves it.

    Model (dual-slope): free-space (1/d^2) below the crossover, the two-ray
    far field (1/d^4) beyond it. The two curves cross at d_bp = 4*pi*h_t*h_r/
    lambda (= pi * the null-spacing breakpoint 4 h_t h_r/lambda); the far-field
    branch is the standard PL = 40 log10 d - 20 log10(h_t h_r) (G=1), so the
    two branches are CONTINUOUS at d_bp -- anchoring the far field to FSPL at
    the null breakpoint instead would leave a 20 log10(pi) ~ 9.9 dB step.
    """
    d = np.asarray(distance_m, dtype=float)
    lam = _C / float(freq_hz)
    d_bp = 4.0 * np.pi * h_tx_m * h_rx_m / lam
    r1 = np.sqrt(d ** 2 + (h_tx_m - h_rx_m) ** 2)
    pl_below = fspl_db(r1, freq_hz)
    pl_above = 40.0 * np.log10(np.maximum(d, 1e-9)) \
        - 20.0 * np.log10(h_tx_m * h_rx_m)
    out = np.where(d <= d_bp, pl_below, pl_above)
    return float(out) if np.ndim(out) == 0 else out


def specular_reflection_point_fraction(h_tx_m: float, h_rx_m: float) -> float:
    """Flat-Earth specular point location as a fraction of d from the TX:
        x_spec / d = h_tx / (h_tx + h_rx).

    For h_tx=30, h_rx=2 -> 0.9375 (i.e. 4.69 km along a 5 km path). Use this to
    pick the lat/lon at which to sample a'/b' for path_loss_spatial_db.
    """
    return h_tx_m / (h_tx_m + h_rx_m)

"""
Two-ray ground reflection model over a flat lunar regolith surface.

**Student 1 (S1) — Week 3 implementation task.**
See TASKS.md § S1-W3 for acceptance criteria and test targets.

Physical model
--------------
At surface-to-surface lunar links (km distances, antenna heights 2–30 m),
the grazing angle is typically θ < 0.5°. In this regime the ground-reflected
ray has nearly equal amplitude to the direct ray but opposite phase (Γ → −1),
causing partial cancellation of the received field.

The two-ray received power (coherent sum of direct + reflected ray):

    E_total = (e^{−jk·r₁} / r₁) + Γ · (e^{−jk·r₂} / r₂)

    r₁ = √(d² + (hₜ − hᵣ)²)   [direct path length]
    r₂ = √(d² + (hₜ + hᵣ)²)   [reflected path length]
    θ  = arctan((hₜ + hᵣ) / d) [grazing angle]
    Γ  = fresnel_coefficients(rho, freq_ghz, θ)

Far-field approximation (d >> breakpoint dₒ = 4·hₜ·hᵣ / λ):
    Pᵣ / Pᵣ_Friis ∝ (hₜ · hᵣ)² / d⁴   → 40 log(d) slope (vs 20 for Friis)

Source equations
-----------------
Rappaport, T. S. (1996). Wireless Communications: Principles and Practice.
    Prentice Hall. Chapter 3, eqs. 3.26–3.30.
    (Standard textbook; Section 3.5 covers the two-ray model.)

Parsons, J. D. (2000). The Mobile Radio Propagation Channel, 2nd ed.
    Wiley. Section 2.3.

Baseline comparison
--------------------
Toonen et al. (2022), "Optimizing Lunar Map Partitioning for Multipath Fade Loss
    Analyses," IEEE J. Radio Freq. Identif., vol. 6, doi:10.1109/JRFID.2022.3159775.
    Uses Fresnel-zone SBR ray-tracing over LOLA DEM (NASA Glenn).
    → Compare your two-ray fade-loss maps against their L99% south-pole results.

Edwards et al. (2023), NTRS 20220015268, uses Friis only (no two-ray).
    → Quantify two-ray correction at 2, 5, 10 km for h_BTS = 30 m, h_UE = 2 m.

Key insight: the breakpoint distance dₒ = 4·hₜ·hᵣ / λ at S-band (λ=0.12 m),
hₜ=30 m, hᵣ=2 m is dₒ ≈ 2 km. Beyond 2 km, path loss goes as 1/d⁴ regardless
of regolith details — the antenna height dominates.
"""

import numpy as np
from .friis import fspl_db
from ..regolith.dielectric import fresnel_coefficients

_C = 2.998e8  # m/s


def breakpoint_distance(
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
) -> float:
    """Critical (breakpoint) distance dₒ = 4·hₜ·hᵣ / λ.

    TODO (S1, Week 3):
        Implement:
            dₒ = 4 · h_tx · h_rx · f / c

        Test targets (hₜ=30 m, hᵣ=2 m):
            breakpoint_distance(30, 2, 0.442e9) ≈   354 m  (UHF 442 MHz)
            breakpoint_distance(30, 2, 2.5e9)   ≈ 2 000 m  (S-band 2.5 GHz)
            breakpoint_distance(30, 2, 8.4e9)   ≈ 6 720 m  (X-band)
            breakpoint_distance(30, 2, 27.0e9)  ≈ 21 600 m (Ka-band)

        Physical meaning: beyond dₒ, received power ∝ 1/d⁴ (not 1/d²).
        At S-band, ALL operational lunar surface links (d > 2 km) are in
        the 1/d⁴ regime. This is the single most important number for
        lunar surface link budget design.

    Returns
    -------
    d_c : float   (metres)
    """
    raise NotImplementedError(
        "TODO (S1, Week 3): implement breakpoint distance formula."
    )


def path_loss_db(
    distance_m: float | np.ndarray,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    rho: float = 1.50,
) -> float | np.ndarray:
    """Two-ray path loss over flat lunar regolith (dB, positive = loss).

    TODO (S1, Week 3):
        Implement the coherent two-ray model:

        1. Compute r₁, r₂, and grazing angle θ from d, hₜ, hᵣ.
        2. Compute Γ = fresnel_coefficients(rho, freq_ghz, θ)[0]   (use V-pol).
        3. Compute the normalised field magnitude:
               |E| = | e^{−jk·r₁}/r₁ + Γ · e^{−jk·r₂}/r₂ |
        4. Express as additional loss vs free-space:
               PL_two_ray [dB] = FSPL(d, f) − 20·log10(|E| · d)

        Implementation tip: use complex exponentials, not the small-angle
        approximation, so the model is valid at all distances including
        near the breakpoint where oscillations are large.

        Test targets:
            At d < breakpoint (100 m), hₜ=30m, hᵣ=2m, f=2.5GHz:
                path_loss_db ≈ fspl_db(100, 2.5e9)  ± 6 dB  (oscillations)
            At d >> breakpoint (10 km), same geometry:
                path_loss_db ≈ fspl_db(10000, 2.5e9) + ~20 dB  (1/d⁴ penalty)
            Baseline check: compare against Toonen et al. (2022) L99% fade-loss
                maps (Fig. 6) using rho=1.50 (εᵣ≈2.69) for qualitative sanity.

    Parameters
    ----------
    distance_m : float or array-like
        Horizontal distance between Tx and Rx in metres.
    h_tx_m : float
        Transmit antenna height above ground in metres.
    h_rx_m : float
        Receive antenna height above ground in metres.
    freq_hz : float
        Carrier frequency in Hz.
    rho : float
        Regolith bulk density in g/cm³ (default 1.50).

    Returns
    -------
    pl_db : float or ndarray
        Two-ray path loss in dB.
    """
    raise NotImplementedError(
        "TODO (S1, Week 3): implement two-ray path loss. "
        "See Rappaport (1996) eqs. 3.26–3.30 and "
        "docs/survey/03-rf-propagation.md"
    )


def path_loss_spatial_db(
    distance_m: float | np.ndarray,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    a_prime_map: np.ndarray,
    b_prime_map: np.ndarray,
    rho: float = 1.50,
    reflection_point_fraction: float = 0.5,
) -> float | np.ndarray:
    """Two-ray path loss with spatially varying loss tangent (Siegler 2020).

    TODO (S1, Week 7):
        Same as path_loss_db() but tan_delta varies spatially using the
        Siegler (2020) a' and b' maps at the specular reflection point:
            tan_delta = a_prime * (freq_hz / 1e9) ** b_prime

        The specular reflection point is at fraction:
            x_spec / d = hₜ / (hₜ + hᵣ)   [flat-Earth approximation]

        For a 5 km path with hₜ=30m, hᵣ=2m: x_spec ≈ 4.69 km from Tx.

        Use lunarcomms.io.pgda.sample_loss_tangent_params() to extract
        a_prime and b_prime from the Siegler 2020 Zenodo files.

        Baseline: compare against path_loss_db() with constant rho=1.50
        to quantify the error from a global average loss tangent.

    Parameters
    ----------
    a_prime_map : ndarray, shape (N,)
        Loss-tangent constant a' at the specular reflection point for each
        distance. From lunarcomms.io.pgda.sample_loss_tangent_params().
    b_prime_map : ndarray, shape (N,)
        Loss-tangent exponent b' at the specular reflection point.
    rho : float
        Bulk density for permittivity ε' = 1.919^rho (constant, default 1.50).
    reflection_point_fraction : float
        Fraction along the path where specular reflection occurs.
        Default 0.5 assumes equal heights (approximate).
    """
    raise NotImplementedError(
        "TODO (S1, Week 7): implement spatially varying two-ray model. "
        "Use sample_loss_tangent_params() for a', b' at specular point."
    )

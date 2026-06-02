"""
Dielectric properties of lunar regolith.

**Student 1 (S1) — Week 2 implementation task.**
See ``TASKS.md`` § S1-W2 for acceptance criteria and test targets.

Source equations to implement
------------------------------
1. Real permittivity — Olhoeft & Strangway (1975), eq. 1:
       ε' = 1.919^ρ      [ρ in g/cm³]
   Full paper (open access via NASA ADS):
   https://ui.adsabs.harvard.edu/abs/1975E%26PSL..24..394O/abstract
   doi:10.1016/0012-821X(75)90102-2

2. Loss tangent — Siegler et al. (2020), eq. 6:
       log₁₀(tan δ) = 0.312·ρ + 0.069·f_GHz − 3.79
   Full paper (AGU open access):
   https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2020JE006405
   doi:10.1029/2020JE006405

3. Fresnel coefficients — Balanis (2012), Advanced Engineering
   Electromagnetics, eqs. 5-17 and 5-18 (TM and TE polarisation,
   grazing-angle convention).

Validation targets (from published tables)
-------------------------------------------
- ρ=1.50 g/cm³          → ε' ≈ 2.69   [Olhoeft 1975, Table 2]
- ρ=1.74 g/cm³          → ε' ≈ 3.20   [Carrier 1991, Table 9.2]
- ρ=1.50, f=2.5 GHz     → tan δ ≈ 0.0082  [Siegler 2020, Fig. 4]
- ρ=1.50, f=27 GHz      → tan δ ≈ 0.0170  [Siegler 2020, Fig. 4]
- θ→0 (grazing)         → |Γ_v| → 1, Γ_v → −1  [physical limit]

Baseline comparison
--------------------
Edwards et al. (2023) IEEE Aerospace ("LTE/5G for the Moon"), NTRS 20220015268,
uses εr = 3.0 (constant) and tan δ = 0 as a single-value baseline.
Your implementation should quantify the error from that simplification
across the south-pole DEM (PGDA-78 density map, Siegler 2020).
"""

import numpy as np


def permittivity(rho: float | np.ndarray) -> float | np.ndarray:
    """Real part of relative permittivity (Olhoeft & Strangway 1975, eq. 1).

    TODO (S1, Week 2):
        Implement the formula:  ε' = 1.919^ρ
        where ρ is bulk density in g/cm³.

        Typical density values (Carrier et al. 1991, Table 9.1):
            Surface (0–2 cm)    : ρ ≈ 1.30 g/cm³  → ε' ≈ 2.30
            Upper layer (0–30 cm): ρ ≈ 1.50 g/cm³  → ε' ≈ 2.69
            Deep regolith (>1 m): ρ ≈ 1.74 g/cm³  → ε' ≈ 3.20
            Consolidated basalt  : ρ ≈ 3.00 g/cm³  → ε' ≈ 6.93

        Test target: permittivity(1.50) ≈ 2.69  (tolerance ±0.01)

    Parameters
    ----------
    rho : float or array-like
        Bulk density in g/cm³.

    Returns
    -------
    eps_prime : float or ndarray
        Real relative permittivity (dimensionless).
    """
    raise NotImplementedError(
        "TODO (S1, Week 2): implement Olhoeft & Strangway (1975) eq. 1. "
        "See docs/survey/04-regolith-dielectrics.md"
    )


def loss_tangent(
    rho: float | np.ndarray,
    freq_ghz: float | np.ndarray,
) -> float | np.ndarray:
    """Loss tangent of lunar regolith (Siegler et al. 2020, eq. 6).

    TODO (S1, Week 2):
        Implement the log-linear fit:
            log₁₀(tan δ) = 0.312·ρ + 0.069·f_GHz − 3.79

        Test targets:
            loss_tangent(1.50, 2.5)  ≈ 0.0082   (S-band)
            loss_tangent(1.50, 0.44) ≈ 0.0054   (UHF)
            loss_tangent(1.50, 27.0) ≈ 0.0170   (Ka-band)

        Note: the frequency dependence (0.069·f) represents dissipation
        from ilmenite (FeTiO₃) content and is NOT in the older
        Olhoeft & Strangway formula. Using tan δ = 0 as in Edwards (2023)
        overestimates received power by ~0.3–0.6 dB per km at S-band.

    Parameters
    ----------
    rho : float or array-like
        Bulk density in g/cm³.
    freq_ghz : float or array-like
        Frequency in GHz.  Valid range: 0.5–37 GHz (Siegler 2020, Fig. 3).

    Returns
    -------
    tan_delta : float or ndarray
        Loss tangent (dimensionless).
    """
    raise NotImplementedError(
        "TODO (S1, Week 2): implement Siegler et al. (2020) eq. 6. "
        "See docs/survey/04-regolith-dielectrics.md"
    )


def complex_permittivity(
    rho: float | np.ndarray,
    freq_ghz: float | np.ndarray,
) -> complex | np.ndarray:
    """Complex relative permittivity  ε = ε'·(1 − j·tan δ).

    TODO (S1, Week 2):
        Call permittivity() and loss_tangent() and combine them.
        No new formula needed — just composition.

    Returns
    -------
    eps : complex ndarray
    """
    raise NotImplementedError(
        "TODO (S1, Week 2): compose permittivity() and loss_tangent(). "
        "See docs/survey/04-regolith-dielectrics.md"
    )


def skin_depth_m(
    rho: float | np.ndarray,
    freq_ghz: float | np.ndarray,
) -> float | np.ndarray:
    """EM skin depth in lunar regolith (metres).

    TODO (S1, Week 2):
        For a low-loss dielectric (tan δ << 1), the skin depth is:
            δ_s = λ₀ / (π · √ε' · tan δ)
        where λ₀ = c / f is the free-space wavelength.

        Source: Ulaby & Long (2014), "Microwave Radar and Radiometric
        Remote Sensing", eq. 2-61. PDF available open-access:
        https://mrs.eecs.umich.edu/

        Test targets at ρ=1.50 g/cm³:
            skin_depth_m(1.50, 2.5)  → ~0.05–0.09 m  (S-band)
            skin_depth_m(1.50, 27.0) → ~0.005–0.009 m (Ka-band)

        Physical interpretation: S-band probes the topmost ~5–9 cm of
        regolith. Ka-band is surface-only. UHF penetrates ~1 m.
        This determines which roughness scale matters for each band.

    Returns
    -------
    delta_s : float or ndarray
        Skin depth in metres.
    """
    raise NotImplementedError(
        "TODO (S1, Week 2): implement low-loss skin depth formula. "
        "See Ulaby & Long (2014) eq. 2-61."
    )


def fresnel_coefficients(
    rho: float | np.ndarray,
    freq_ghz: float | np.ndarray,
    theta_rad: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Fresnel reflection coefficients for an air–regolith interface.

    TODO (S1, Week 3):
        Implement TM (vertical) and TE (horizontal) Fresnel coefficients
        using the *grazing angle* convention (θ measured from horizontal):

            Γ_v = (ε_c·sin θ − √(ε_c − cos²θ)) / (ε_c·sin θ + √(ε_c − cos²θ))
            Γ_h = (sin θ − √(ε_c − cos²θ))      / (sin θ + √(ε_c − cos²θ))

        where ε_c = complex_permittivity(rho, freq_ghz).

        Source: Balanis (2012), Advanced Engineering Electromagnetics,
        2nd ed., eqs. 5-17b and 5-18b. ISBN 978-0-470-58948-9.
        Also: Rappaport (1996), Wireless Communications, Appendix B.

        Physical limits to verify:
            θ → 0  (grazing):   Γ_v → −1,  Γ_h → −1
            θ = π/2 (broadside): |Γ_v| minimised at Brewster angle
                                  ε'=2.69 → θ_B = arctan(√ε') ≈ 58.5°

        Test targets:
            At θ=0.01 rad, ρ=1.50, f=2.5 GHz:
                |Γ_v| > 0.95   (near-grazing → near-total reflection)
                |Γ_h| > 0.95
            At θ=π/2, ρ=1.50, f=2.5 GHz:
                Γ_h.real < 0   (always negative for TE)

    Parameters
    ----------
    rho : float or array-like
        Regolith bulk density in g/cm³.
    freq_ghz : float or array-like
        Frequency in GHz.
    theta_rad : float or array-like
        Grazing angle in radians [0, π/2].

    Returns
    -------
    gamma_v : complex ndarray   (TM / vertical polarisation)
    gamma_h : complex ndarray   (TE / horizontal polarisation)
    """
    raise NotImplementedError(
        "TODO (S1, Week 3): implement Fresnel coefficients. "
        "See Balanis (2012) eqs. 5-17b, 5-18b and "
        "docs/survey/04-regolith-dielectrics.md"
    )

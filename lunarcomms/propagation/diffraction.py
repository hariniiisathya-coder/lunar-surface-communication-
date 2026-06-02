"""
Terrain diffraction loss — ITU-R P.526-15 (Deygout multi-edge method).

**Student 1 (S1) — Week 4 implementation task.**
See TASKS.md § S1-W4.

Physical model
--------------
When the direct path between BTS and UE is blocked by a crater rim or
ridge, the signal diffracts over the edge. The ITU-R P.526-15 knife-edge
model computes the additional attenuation as a function of the Fresnel-
Kirchhoff diffraction parameter ν.

For a single knife-edge obstacle of height h above the line of sight,
with distances d₁ (Tx→edge) and d₂ (edge→Rx):

    ν = h · √(2·(d₁ + d₂) / (λ·d₁·d₂))
         = h · √(2/λ · (1/d₁ + 1/d₂))

    J(ν) ≈ 6.9 + 20·log10(√((ν−0.1)² + 1) + ν − 0.1)  dB    [ν > −0.78]

For multiple edges (Deygout method): apply the dominant-edge approximation
iteratively — find the edge with maximum ν, compute its diffraction loss,
then recurse on the sub-paths.

Source equations
-----------------
ITU-R Recommendation P.526-15 (2019). Propagation by diffraction.
    Available free: https://www.itu.int/rec/R-REC-P.526/en
    See Section 4.1 (knife-edge), Section 4.2 (multiple edges / Deygout).

Boithias, L. (1987). Radio Wave Propagation. North Oxford Academic.
    Chapter 4 (Deygout original method reference).

Baseline comparison
--------------------
The lunar south-pole terrain has crater rims 200–2 000 m above surrounding
plains. At S-band (λ=0.12 m) with a 200-m rim peak midway between BTS and
rover at 5 km separation:

    ν = 200 · √(2/(0.12 · 2500 · 2500)) ≈ 11.5
    J(ν) ≈ 33 dB

Compare to UHF (λ=0.68 m): ν ≈ 4.9, J ≈ 26 dB.
Ka-band (λ=0.011 m): ν ≈ 38, J ≈ 44 dB.

Published benchmark:
Toonen et al. (2021) do NOT include terrain diffraction (line-of-sight only).
Jun et al. (2025), IEEE Access, adds diffraction over LOLA terrain profiles
for equatorial links. Your task: apply Deygout to PGDA-78 south-pole profiles.
"""

import numpy as np


def fresnel_kirchhoff_parameter(
    h_m: float | np.ndarray,
    d1_m: float | np.ndarray,
    d2_m: float | np.ndarray,
    freq_hz: float,
) -> float | np.ndarray:
    """Fresnel-Kirchhoff diffraction parameter ν.

    TODO (S1, Week 4):
        Implement:
            ν = h · √(2/λ · (1/d₁ + 1/d₂))
              = h · √(2·f/c · (d₁+d₂)/(d₁·d₂))

        where h is the height of the obstacle ABOVE the straight line
        connecting Tx and Rx (positive = obstacle above LOS,
        negative = clearance below LOS).

        Test targets:
            fresnel_kirchhoff_parameter(200, 2500, 2500, 2.5e9) ≈ 11.5
            fresnel_kirchhoff_parameter(-10, 2500, 2500, 2.5e9) < 0  (clearance)
            fresnel_kirchhoff_parameter(0,  2500, 2500, 2.5e9) ≈ 0   (grazing)

    Parameters
    ----------
    h_m : height of obstacle above Tx–Rx line of sight (metres).
          Negative = obstacle below LOS (clearance).
    d1_m : distance Tx → obstacle (metres).
    d2_m : distance obstacle → Rx (metres).
    freq_hz : carrier frequency (Hz).

    Returns
    -------
    nu : float or ndarray
    """
    raise NotImplementedError(
        "TODO (S1, Week 4): implement Fresnel-Kirchhoff parameter. "
        "See ITU-R P.526-15, eq. (13)."
    )


def knife_edge_loss_db(nu: float | np.ndarray) -> float | np.ndarray:
    """Knife-edge diffraction loss J(ν) in dB (positive = loss).

    TODO (S1, Week 4):
        Implement the ITU-R P.526-15 approximation (Section 4.1, eq. 14):

            J(ν) = 0                                          if ν < −0.78
            J(ν) = 6.9 + 20·log10(√((ν−0.1)² + 1) + ν−0.1)  if ν ≥ −0.78

        Test targets:
            knife_edge_loss_db(-1.0) ≈ 0 dB      (deep clearance, no loss)
            knife_edge_loss_db(0.0)  ≈ 6 dB      (grazing, −6 dB vs free space)
            knife_edge_loss_db(1.0)  ≈ 12.0 dB
            knife_edge_loss_db(11.5) ≈ 33 dB     (200-m rim at S-band)
            knife_edge_loss_db(38)   ≈ 44 dB     (200-m rim at Ka-band)

        Cross-check: ITU-R P.526-15 Table 1 gives J for integer ν values.

    Parameters
    ----------
    nu : float or array-like
        Fresnel-Kirchhoff diffraction parameter.

    Returns
    -------
    J_db : float or ndarray
        Diffraction loss in dB.
    """
    raise NotImplementedError(
        "TODO (S1, Week 4): implement knife-edge loss. "
        "See ITU-R P.526-15, eq. (14) and Table 1."
    )


def deygout_loss_db(
    profile_heights_m: np.ndarray,
    profile_distances_m: np.ndarray,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    max_edges: int = 3,
) -> float:
    """Multi-edge diffraction loss via the Deygout method (dB).

    TODO (S1, Week 4–5):
        Implement the Deygout dominant-edge algorithm:

        1. Given a terrain height profile (h[i] at distance x[i]):
           a. Compute the height of each profile point ABOVE the Tx–Rx line.
           b. Find the index i* with maximum ν (dominant edge).
           c. Compute J(ν_i*) as the main diffraction loss.
           d. Recursively apply steps a–c to the sub-paths
              [Tx → i*] and [i* → Rx], up to max_edges total.
           e. Sum all J values.

        Source: ITU-R P.526-15, Section 4.2.2 (Deygout modified method).
        Also: Boithias (1987) for original formulation.

        Validation: for a single knife-edge at the midpoint, deygout_loss_db()
        must match knife_edge_loss_db(fresnel_kirchhoff_parameter(...)) exactly.

        Lunar application:
            Input a 1-D profile extracted from PGDA-78 DEM along the great-circle
            path between BTS and UE (use lunarcomms.io.pgda.extract_profile()).
            Output the diffraction loss to add to the two-ray path loss.

    Parameters
    ----------
    profile_heights_m : ndarray, shape (N,)
        Terrain elevation in metres (lunar surface, PGDA-78 datum).
    profile_distances_m : ndarray, shape (N,)
        Cumulative distance along path in metres (same length as heights).
    h_tx_m : float
        Transmit antenna height above terrain at Tx location.
    h_rx_m : float
        Receive antenna height above terrain at Rx location.
    freq_hz : float
        Carrier frequency in Hz.
    max_edges : int
        Maximum number of dominant edges to consider (default 3).

    Returns
    -------
    loss_db : float
        Total multi-edge diffraction loss in dB.
    """
    raise NotImplementedError(
        "TODO (S1, Week 4–5): implement Deygout multi-edge diffraction. "
        "See ITU-R P.526-15 Section 4.2.2."
    )

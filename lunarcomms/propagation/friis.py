"""
Free-space path loss — Friis transmission equation.

**Shared module (S1 + S2) — Week 2 implementation task.**
See TASKS.md §§ S1-W2, S2-W4.

Source equations
-----------------
Friis, H. T. (1946). A note on a simple transmission formula.
    *Proceedings of the IRE*, 34(5), 254–256.
    doi:10.1109/JRPROC.1946.234568
    (freely readable at IEEE Xplore)

ITU-R P.525-4 (2019). Calculation of free-space attenuation.
    https://www.itu.int/rec/R-REC-P.525/en

Notes on the lunar context
---------------------------
On the lunar surface there is no atmosphere, so free-space conditions
hold exactly for the direct ray (no tropospheric absorption, no rain fade,
no ionospheric refraction above ~1 GHz). Departures from Friis come only from:
  1. Ground reflection at grazing incidence (two_ray.py).
  2. Terrain blockage and diffraction over crater rims (diffraction.py).
  3. Regolith surface scattering at high elevation angles (future work).

Baseline: Edwards et al. (2023), NTRS 20220015268, Table III uses Friis only
and reports ~–128 dBm received power at 10 km from a 30-m BTS (S-band, 23 dBm
transmit). Your implementation should reproduce this number ±1 dB as a sanity
check before adding the two-ray correction.
"""

import numpy as np

_C = 2.998e8  # speed of light, m/s


def fspl_db(
    distance_m: float | np.ndarray,
    freq_hz: float | np.ndarray,
) -> float | np.ndarray:
    """Free-space path loss in dB (positive = loss).

    TODO (S1/S2, Week 2):
        Implement:
            FSPL [dB] = 20·log10(4π·d·f / c)
                      = 20·log10(d) + 20·log10(f) − 147.55

        Sanity check (reproduce Edwards 2023, Table III):
            fspl_db(10_000, 2.5e9) ≈ 130.4 dB

    Parameters
    ----------
    distance_m : float or array-like
        Link distance in metres.
    freq_hz : float or array-like
        Carrier frequency in Hz.

    Returns
    -------
    fspl : float or ndarray
        Free-space path loss in dB.
    """
    raise NotImplementedError(
        "TODO (S1/S2, Week 2): implement Friis FSPL. "
        "See ITU-R P.525-4 and docs/survey/03-rf-propagation.md"
    )


def received_power_dbm(
    eirp_dbm: float | np.ndarray,
    path_loss_db: float | np.ndarray,
    rx_gain_dbi: float | np.ndarray = 0.0,
    rx_losses_db: float | np.ndarray = 0.0,
) -> float | np.ndarray:
    """Received power in dBm (standard link budget equation).

    TODO (S1/S2, Week 2):
        Implement:
            P_rx [dBm] = EIRP [dBm] − PL [dB] + G_rx [dBi] − L_rx [dB]

        Sanity check:
            received_power_dbm(eirp_dbm=53, path_loss_db=130.4,
                               rx_gain_dbi=0, rx_losses_db=3)
            → ≈ −80.4 dBm

    Parameters
    ----------
    eirp_dbm : float or array-like
        Transmitter EIRP in dBm.
    path_loss_db : float or array-like
        Total path loss in dB (positive = loss).
    rx_gain_dbi : float or array-like
        Receiver antenna gain in dBi (default 0 = isotropic).
    rx_losses_db : float or array-like
        Rx implementation + feeder losses in dB (default 0).

    Returns
    -------
    p_rx : float or ndarray
        Received power in dBm.
    """
    raise NotImplementedError(
        "TODO (S1/S2, Week 2): implement link budget power equation."
    )


def link_margin_db(
    p_rx_dbm: float | np.ndarray,
    sensitivity_dbm: float | np.ndarray,
) -> float | np.ndarray:
    """Link margin in dB (positive = link closes).

    TODO (S1/S2, Week 2):
        Implement:  margin = P_rx − sensitivity

        Typical 5G NR sensitivity for 20 MHz NR at MCS-0 (QPSK, R=1/8):
            sensitivity ≈ −106 dBm (NR UE class 3, NF=9 dB)
        Source: 3GPP TS 38.101-1, Table 7.3.2-1.

    Returns
    -------
    margin : float or ndarray
        Link margin in dB. Negative → link does not close.
    """
    raise NotImplementedError(
        "TODO (S1/S2, Week 2): implement link margin. "
        "See 3GPP TS 38.101-1 Table 7.3.2-1 for sensitivity reference."
    )


def max_range_m(
    eirp_dbm: float,
    rx_gain_dbi: float,
    sensitivity_dbm: float,
    freq_hz: float,
    margin_db: float = 0.0,
) -> float:
    """Maximum free-space range for a given link budget.

    TODO (S1/S2, Week 2):
        Invert fspl_db() to find the distance d at which the link margin
        equals margin_db:
            d = (c / (4π·f)) · 10^((EIRP + G_rx − sens − margin) / 20)

        Sanity check: reproduce the EIRP = 53 dBm, f = 2.5 GHz,
        sensitivity = −106 dBm, margin = 3 dB case from Edwards (2023)
        Table III: d_max ≈ 8.5 km.

    Parameters
    ----------
    eirp_dbm : float
        Transmitter EIRP in dBm.
    rx_gain_dbi : float
        Receiver antenna gain in dBi.
    sensitivity_dbm : float
        Receiver sensitivity in dBm.
    freq_hz : float
        Carrier frequency in Hz.
    margin_db : float
        Required link margin in dB (default 0).

    Returns
    -------
    d_max : float
        Maximum link distance in metres.
    """
    raise NotImplementedError(
        "TODO (S1/S2, Week 2): invert fspl_db() for max range."
    )

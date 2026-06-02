"""
Elliptical Lunar Frozen Orbit (ELFO) propagation and design.

**Students S2 + S3 — Week 3–4 implementation task.**
See TASKS.md §§ S2-W4, S3-W3.

What is an ELFO?
-----------------
An ELFO is a highly elliptical lunar orbit with its apoapsis over the
lunar pole of interest. The Folta-Quinn (2006) solution selects orbital
elements that cancel secular drift of eccentricity and argument of perigee,
creating a "frozen" orbit that requires no station-keeping for 1–2 years.

Key ELFO parameters (Lunar Pathfinder / Moonlight design):
    Semi-major axis:   a ≈ 6 141.7 km   (R_moon + mean altitude)
    Eccentricity:      e ≈ 0.60
    Inclination:       i ≈ 57.7°         (Folta-Quinn frozen condition)
    Arg. of perigee:   ω ≈ 90°           (apoapsis over south pole)
    Perilune altitude: ~700 km
    Apolune altitude:  ~7 300 km
    Period:            ~10 h

Physical consequence: the satellite spends ~8 of every 10 h near apoapsis
(above the south pole), providing extended communication windows compared
to a circular LLO (10-min windows every 2 h).

Source equations / references
-------------------------------
Folta, D. & Quinn, D. (2006). Lunar frozen orbits.
    AIAA/AAS Astrodynamics Specialist Conference, AIAA 2006-6749.
    https://arc.aiaa.org/doi/10.2514/6.2006-6749
    (NASA NTRS open access: https://ntrs.nasa.gov/citations/20060028369)

Whitley, R. J. & Martinez, R. (2016). Options for staging orbits in
    cislunar space. *IEEE Aerospace Conference*, 2016.
    doi:10.1109/AERO.2016.7500519
    (covers NRHO and comparisons with ELFO for Gateway)

ESA Lunar Pathfinder factsheet:
    https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Lunar_Pathfinder

LCRNS Reference Constellation 3.1 (NTRS 20250002698):
    https://ntrs.nasa.gov/citations/20250002698
    (contains the NASA-defined LCRNS ELFO parameters for south pole)
"""

import numpy as np

R_MOON_KM = 1737.4  # IAU 2015 mean radius


# ---------------------------------------------------------------------------
# Keplerian propagation (two-body)
# ---------------------------------------------------------------------------

def keplerian_state(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    aop_deg: float,
    true_anomaly_deg: float,
    gm_km3s2: float = 4902.800066,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert Keplerian elements to Cartesian state (position, velocity) in km, km/s.

    TODO (S2/S3, Week 3):
        Implement the standard Keplerian to Cartesian conversion:
        1. Compute semi-latus rectum p = a·(1−e²).
        2. Compute position in perifocal frame (PQW):
               r_pqw = (p/(1+e·cos ν)) · [cos ν, sin ν, 0]
        3. Compute velocity in perifocal frame:
               v_pqw = √(μ/p) · [−sin ν, e+cos ν, 0]
        4. Apply rotation matrix R₃(−RAAN)·R₁(−i)·R₃(−ω) to transform
           from PQW to ECI (MOON_ME or ECLIPJ2000 depending on epoch).

        Source: Bate, Mueller & White (1971), *Fundamentals of Astrodynamics*,
        Section 2.4 (freely available via archive.org).
        doi: (no doi; original Dover edition)
        Archive.org: https://archive.org/details/fundamentalsofas00bate

        Test targets (Lunar Pathfinder nominal orbit):
            sma=6141.7, ecc=0.60, inc=57.7, raan=0, aop=90, ν=0
            → perilune ≈ 700 km altitude → r_perilune ≈ 2437.4 km from Moon center
            → |pos| should be ~2437.4 km at true anomaly 0°

    Parameters
    ----------
    sma_km : float   Semi-major axis in km.
    ecc : float      Eccentricity [0, 1).
    inc_deg : float  Inclination in degrees.
    raan_deg : float Right ascension of ascending node in degrees.
    aop_deg : float  Argument of perigee in degrees.
    true_anomaly_deg : float  True anomaly in degrees.
    gm_km3s2 : float  Gravitational parameter μ (default: lunar GM, km³/s²).

    Returns
    -------
    pos_km : ndarray, shape (3,)
    vel_km_s : ndarray, shape (3,)
    """
    raise NotImplementedError(
        "TODO (S2/S3, Week 3): implement Keplerian→Cartesian. "
        "See Bate, Mueller & White (1971) Section 2.4. "
        "https://archive.org/details/fundamentalsofas00bate"
    )


def propagate_elfo(
    sma_km: float,
    ecc: float,
    inc_deg: float,
    raan_deg: float,
    aop_deg: float,
    t0_et: float,
    t_span_s: float,
    dt_s: float = 60.0,
    gm_km3s2: float = 4902.800066,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate an ELFO in two-body Keplerian motion.

    TODO (S2/S3, Week 3):
        1. Compute the mean motion:  n = √(μ / a³)  [rad/s]
        2. For each time step:
           a. Advance mean anomaly:  M(t) = M₀ + n·(t − t₀)
           b. Solve Kepler's equation:  M = E − e·sin(E)  [Newton-Raphson]
           c. Convert E → true anomaly ν via:
                  tan(ν/2) = √((1+e)/(1−e)) · tan(E/2)
           d. Call keplerian_state() with ν(t) to get pos/vel.

        Source: Bate, Mueller & White (1971) Section 4.2 (Kepler's equation).
        Kepler's equation solver: scipy.optimize.brentq is acceptable but
        Newton-Raphson is ≥10× faster and converges in <10 iterations.

        Validation against GMAT:
            Propagate Lunar Pathfinder orbit for 24 h. Compare periapsis
            altitude (should stay ~700 km ± 50 km over one orbit).
            Note: two-body ignores mascons; use as first approximation only.
            For mascon effects, see GMAT script in data/orbits/gmat_elfo.script.

    Parameters
    ----------
    t0_et : float      Initial SPICE ephemeris time.
    t_span_s : float   Total propagation time in seconds.
    dt_s : float       Time step in seconds (default 60 s).

    Returns
    -------
    times_et : ndarray, shape (N,)   Ephemeris times.
    positions_km : ndarray, shape (N, 3)   Cartesian positions in km.
    """
    raise NotImplementedError(
        "TODO (S2/S3, Week 3): implement two-body ELFO propagator. "
        "Solve Kepler's equation with Newton-Raphson. "
        "See Bate et al. (1971) Section 4.2."
    )


def south_pole_elevation_deg(
    positions_km: np.ndarray,
) -> np.ndarray:
    """Elevation angle of the satellite above the lunar south pole (degrees).

    TODO (S2/S3, Week 3):
        The south pole is at (0, 0, −R_moon) in MOON_ME Cartesian.
        For each satellite position:
        1. Compute vector from south pole to satellite.
        2. The elevation is 90° − angle between this vector and the
           nadir vector at the south pole (which is just −z_hat).

        Test targets (Lunar Pathfinder ELFO, i=57.7°, ω=90°):
            - Near apoapsis (above south pole): elevation ≈ 40–80° (depends on RAAN)
            - Near perilune: elevation can go negative (satellite below horizon)
            - Maximum elevation per orbit should be ≥ 30° for useful S-band link

        Validation: compare against Figure 3 of
        Iiyama, K. et al. (2023). Autonomous Distributed Lunar Navigation.
        *Navigation*, 70(1). doi:10.33012/navi.560
        (covers elevation angle statistics for ELFO constellations at south pole)

    Parameters
    ----------
    positions_km : ndarray, shape (N, 3)
        Satellite positions in MOON_ME frame.

    Returns
    -------
    elevation_deg : ndarray, shape (N,)
    """
    raise NotImplementedError(
        "TODO (S2/S3, Week 3): compute satellite elevation above south pole. "
        "Validate against Iiyama et al. (2023) Fig. 3."
    )


def contact_windows(
    elevation_deg: np.ndarray,
    times_et: np.ndarray,
    min_elevation_deg: float = 5.0,
) -> list[tuple[float, float]]:
    """Extract contact windows where satellite elevation ≥ min_elevation_deg.

    TODO (S3, Week 4):
        Find contiguous intervals where elevation_deg ≥ min_elevation_deg.
        Return as list of (start_et, end_et) tuples.

        For DTN contact plans, each window becomes one contact entry:
            contact <start_et> <end_et> <node_relay> <node_surface> <data_rate_bps>

        Test targets (Lunar Pathfinder ELFO, one 24-h window):
            - Number of contact windows ≈ 2–3 (one per orbit, ~10 h period)
            - Window duration ≈ 6–9 h per orbit (satellite spends most time at apoapsis)
            - Total coverage ≥ 60% of 24 h  (key LCRNS requirement from SRD)

    Returns
    -------
    windows : list of (start_et, end_et) tuples (SPICE ephemeris time, float)
    """
    raise NotImplementedError(
        "TODO (S3, Week 4): extract contact windows from elevation time series. "
        "Output format compatible with ION-DTN contact plan format."
    )

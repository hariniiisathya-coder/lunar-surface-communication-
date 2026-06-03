"""
Lunar coordinate frames and Earth–Moon–relay geometry via SPICE.

**Shared module (S1 + S2 + S3) — Week 3 implementation task.**
See TASKS.md §§ S1-W3, S2-W4, S3-W3.

Coordinate systems used
------------------------
MOON_ME (Mean Earth / Polar Axis):
    x-axis points toward mean sub-Earth point on the equator.
    z-axis aligned with mean rotation pole.
    Used by: all PGDA cartographic products (DEMs, maps).
    Reference: NAIF PCK frame kernel moon_de440_220930.tf

MOON_PA (Principal Axis):
    x-axis aligned with the principal moment of inertia axis.
    z-axis aligned with angular momentum vector.
    Used by: DE440 ephemerides.
    Differs from ME by ~270 m at the equator (Rambaux & Williams 2011).
    Reference: NAIF frame kernel moon_de440_220930.tf

ECLIPJ2000:
    Standard inertial frame. x-axis toward vernal equinox.
    Used by: SPICE SPK kernel positions.

Why the ME/PA distinction matters
-----------------------------------
PGDA DEMs are in MOON_ME. SPICE SPK ephemerides for spacecraft
(e.g. LCRNS) are computed in ECLIPJ2000 with the Moon body frame
defined as MOON_PA in DE440. Using MOON_ME for surface positions
and MOON_PA for satellite positions without rotating between them
introduces errors up to ~270 m (Park et al. 2021, DE440 paper).

Reference kernels (download with data/download_kernels.py):
    de440.bsp       — planetary ephemerides, includes Moon, Earth, Sun
    moon_de440_220930.tf  — Moon frame kernel (ME↔PA rotation)
    moon_pa_de440_200625.bpc — Moon PCK (pole orientation)
    latest_leapseconds.tls  — leap seconds
    naif0012.tls            — leap seconds (alternative)

Source equations / references
-------------------------------
Park, R. S. et al. (2021). The JPL Planetary and Lunar Ephemerides DE440 and
    DE441. *The Astronomical Journal*, 161(3), 105.
    doi:10.3847/1538-3881/abd414
    https://iopscience.iop.org/article/10.3847/1538-3881/abd414

Rambaux, N. & Williams, J. G. (2011). The Moon's physical librations and
    determination of their free modes. *Celestial Mechanics and Dynamical
    Astronomy*, 109, 85–100. doi:10.1007/s10569-010-9314-2

NAIF SPICE toolkit tutorials:
    https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/
    (Tutorial 17: Reference frames and coordinate systems)

SpiceyPy documentation:
    https://spiceypy.readthedocs.io/en/stable/
"""

from __future__ import annotations

import numpy as np

try:
    import spiceypy as spice  # noqa: F401
    _SPICE_AVAILABLE = True
except ImportError:
    _SPICE_AVAILABLE = False


def load_kernels(kernel_dir: str = "data/kernels") -> None:
    """Load SPICE kernels required for lunar geometry.

    TODO (all students, Week 3, Day 1):
        Use spiceypy.furnsh() to load the following kernel files in order:
            1. {kernel_dir}/latest_leapseconds.tls
            2. {kernel_dir}/de440.bsp
            3. {kernel_dir}/moon_pa_de440_200625.bpc
            4. {kernel_dir}/moon_de440_220930.tf

        After loading, verify the kernel pool with spice.ktotal('ALL').
        Expected total: ≥ 4 kernels.

        Source: NAIF tutorial "SPICE Kernel Loading".
        URL: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/

        Sanity check (run after loading):
            et = spice.str2et("2026-01-01T00:00:00")
            pos, lt = spice.spkpos("MOON", et, "ECLIPJ2000", "NONE", "EARTH")
            # pos should be ~[-2e5, 3e5, 1e5] km range 350 000–400 000 km

    Parameters
    ----------
    kernel_dir : str
        Path to directory containing SPICE kernel files.
    """
    raise NotImplementedError(
        "TODO (all, Week 3): load SPICE kernels with spiceypy.furnsh(). "
        "See NAIF tutorial: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/"
    )


def earth_moon_distance_km(et: float | np.ndarray) -> float | np.ndarray:
    """Earth–Moon distance in km at ephemeris time(s) et.

    TODO (all students, Week 3):
        Use spice.spkpos() to get the Moon position relative to Earth
        (or Earth relative to Moon) in ECLIPJ2000, then compute the norm.

            pos, lt = spice.spkpos("MOON", et, "ECLIPJ2000", "NONE", "EARTH")
            distance_km = np.linalg.norm(pos)

        Validation against JPL Horizons (https://ssd.jpl.nasa.gov/horizons/):
            2026-Jan-01 00:00 UT → ~389 000 km  (check Horizons for exact value)
            Varies between ~356 500 km (perigee) and ~406 700 km (apogee).
            One-way light time: ~1.18–1.36 s.

        This sets the Earth-Moon propagation delay used in S2 (5G MAC timer
        analysis) and S3 (DTN contact plan, delay distribution).

    Parameters
    ----------
    et : float or array-like
        SPICE ephemeris time (seconds past J2000).

    Returns
    -------
    dist_km : float or ndarray
    """
    raise NotImplementedError(
        "TODO (all, Week 3): compute Earth-Moon distance via spice.spkpos(). "
        "Validate against JPL Horizons: https://ssd.jpl.nasa.gov/horizons/"
    )


def surface_to_inertial(
    lon_deg: float,
    lat_deg: float,
    alt_m: float,
    frame: str = "MOON_ME",
) -> np.ndarray:
    """Convert lunar surface position to inertial Cartesian (km).

    TODO (S1/S3, Week 3):
        Use spice.pgrrec() (planetographic to rectangular) with:
            body = "MOON"
            lon, lat in radians
            alt in km above reference sphere (R_moon = 1737.4 km)
            Then rotate from MOON_ME to ECLIPJ2000 at a reference epoch
            using spice.pxform().

        Source: SpiceyPy docs, spice.pgrrec() and spice.pxform().
        URL: https://spiceypy.readthedocs.io/en/stable/documentation.html

    Parameters
    ----------
    lon_deg : float   Longitude in degrees (planetocentric, east positive).
    lat_deg : float   Latitude in degrees (planetocentric).
    alt_m : float     Altitude above mean lunar radius in metres.
    frame : str       Output frame ('MOON_ME' or 'ECLIPJ2000').

    Returns
    -------
    pos_km : ndarray, shape (3,)   Position in km.
    """
    raise NotImplementedError(
        "TODO (S1/S3, Week 3): implement surface_to_inertial() via spice.pgrrec()."
    )


def earth_elevation_angle_deg(
    surface_lon_deg: float,
    surface_lat_deg: float,
    et: float,
) -> float:
    """Elevation angle to Earth as seen from a lunar surface point (degrees).

    TODO (S1/S3, Week 3):
        1. Get position of Earth relative to surface point in MOON_ME frame.
        2. Convert to topocentric AZ/EL using spice.reclat() or spice.recazl().
        3. Elevation < 0 → Earth below horizon (blocked by terrain or limb).

        Sanity check: at the lunar south pole (lat=−90°), the Earth is near
        the horizon (~5–7° elevation, varying with libration).
        At the lunar equator (sub-Earth point), Earth is at ~90° elevation.

        Source: NAIF tutorial "Computing Geometry Using SpiceyPy".
        URL: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/

    Returns
    -------
    el_deg : float   Elevation angle in degrees (negative = below horizon).
    """
    raise NotImplementedError(
        "TODO (S1/S3, Week 3): compute Earth elevation angle from surface "
        "point using SPICE. Cross-check that south pole gives ~5–7°."
    )

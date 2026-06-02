"""
LCRNS Reference Constellation 3.1 and Moonlight ELFO loaders.

**Students S2 + S3 — Week 4 implementation task.**
See TASKS.md §§ S2-W5, S3-W4.

Public data source
-------------------
LCRNS Reference Constellation 3.1 is published as a NASA Technical Report:

    Guinn, J. R. et al. (2025). Lunar Communications Relay and Navigation
    Services (LCRNS) Reference Constellation Design 3.1.
    NASA Technical Reports Server, NTRS 20250002698.
    https://ntrs.nasa.gov/citations/20250002698

The report provides:
  - Orbital elements for a 2-satellite ELFO constellation.
  - Ground track / coverage statistics for the lunar south pole.
  - Contact window analysis (Table 5, hourly coverage fractions).
  - Frequency plan (S-band and Ka-band, compatible with SFCG REC 32-2R5).

Moonlight / Lunar Pathfinder parameters (public ESA factsheet):
    https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Lunar_Pathfinder
    Nominal orbit: a=6141.7 km, e=0.60, i=57.7°, ω=90° (apoapsis south pole)
    Launch: NET Q4 2026.

This module loads the orbital elements from data/orbits/lcrns_ref_constellation.json
and provides convenience functions to propagate them and assess coverage.
"""

import json
from pathlib import Path
import numpy as np

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "orbits"


def load_lcrns_elements(
    json_path: str | Path | None = None,
) -> list[dict]:
    """Load LCRNS Reference Constellation 3.1 orbital elements from JSON.

    TODO (S2/S3, Week 4):
        Read data/orbits/lcrns_ref_constellation.json and return a list of
        dicts, one per satellite, with keys:
            'name', 'sma_km', 'ecc', 'inc_deg', 'raan_deg', 'aop_deg',
            'mean_anomaly_deg_at_epoch', 'epoch_utc', 'source'.

        The JSON file is pre-populated with values from NTRS 20250002698.
        Validate by checking that the perilune altitude of each satellite
        is in the range 600–900 km (Table 3 of the report).

    Returns
    -------
    satellites : list of dict
    """
    raise NotImplementedError(
        "TODO (S2/S3, Week 4): load LCRNS orbital elements from JSON. "
        "Source: NTRS 20250002698 — https://ntrs.nasa.gov/citations/20250002698"
    )


def coverage_fraction(
    elevation_time_series_deg: np.ndarray,
    min_elevation_deg: float = 5.0,
) -> float:
    """Fraction of time that at least one LCRNS satellite is above min elevation.

    TODO (S2/S3, Week 4):
        Given elevation time series for all satellites in the constellation,
        compute the fraction of samples where max(elevation) ≥ min_elevation_deg.

        Validation target (NTRS 20250002698, Table 5):
            2-satellite constellation → ≥ 95% coverage at lunar south pole
            at min elevation 5°.
            1-satellite baseline → ~55–65% coverage.

    Parameters
    ----------
    elevation_time_series_deg : ndarray, shape (N_satellites, N_times)
    min_elevation_deg : float

    Returns
    -------
    fraction : float  in [0, 1]
    """
    raise NotImplementedError(
        "TODO (S2/S3, Week 4): compute LCRNS coverage fraction. "
        "Validate against NTRS 20250002698 Table 5 (≥95% for 2-sat)."
    )


def export_contact_plan(
    windows_by_satellite: list[list[tuple[float, float]]],
    surface_node_id: str = "lander_01",
    data_rate_bps: int = 100_000,
    output_path: str | Path | None = None,
) -> str:
    """Export contact windows to ION-DTN contact plan format.

    TODO (S3, Week 5):
        Generate a contact plan file compatible with:
        - ION-DTN ionrc format: https://sourceforge.net/projects/ion-dtn/
        - DSNS contact plan CSV: https://github.com/ssloxford/DSNS

        Each contact window becomes a line:
            a contact <start_sec> <end_sec> <relay_node> <surface_node> <rate_bps>
            a range   <start_sec> <end_sec> <relay_node> <surface_node> <owlt_s>

        Where:
            start_sec, end_sec = window start/end in seconds from J2000
            owlt_s = one-way light time from relay to surface (from ephemeris)

        Gap in the community: no public contact plan generator exists for
        the LCRNS/Moonlight constellation (as of June 2025). This function
        fills that gap and is independently publishable as a tool paper.
        Target venue: SoftwareX or JOSS (Journal of Open Source Software).

    Parameters
    ----------
    windows_by_satellite : list of lists
        Outer list: one per satellite; inner list: (start_et, end_et) windows.
    surface_node_id : str
        ION node identifier for the surface asset.
    data_rate_bps : int
        Link data rate for the contact plan (default 100 kbps).
    output_path : Path or None
        If given, write to file. Otherwise return as string.

    Returns
    -------
    contact_plan_str : str
    """
    raise NotImplementedError(
        "TODO (S3, Week 5): implement ION-DTN contact plan exporter. "
        "This is the publishable gap in the community. "
        "See ION-DTN ionrc format: https://sourceforge.net/projects/ion-dtn/"
    )

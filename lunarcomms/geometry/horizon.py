"""
Horizon mask and line-of-sight computation from PGDA DEM.

**Student 1 (S1) — Week 3–4 implementation task.**
See TASKS.md § S1-W3.

Horizon masking is the most computationally expensive step in the
coverage pipeline. For a DEM of N×N pixels, a naive raycasting loop
is O(N³). The implementation here must be vectorised with NumPy.

Source / algorithm
-------------------
Mazarico, E. et al. (2011). Illumination conditions of the lunar polar
    regions using LOLA topography. *Icarus*, 211(2), 1066–1081.
    doi:10.1016/j.icarus.2010.10.030
    (open access preprint: https://ntrs.nasa.gov/citations/20100039014)

    Mazarico computes horizon elevation angles in 360 directions from each
    DEM pixel to determine illumination fraction. Adapt the same algorithm
    to determine line-of-sight between a fixed Tx (BTS) and all Rx positions
    on the DEM (rover locations).

Validation: Table 1 of Mazarico (2011) gives illumination fractions at
    specific south-pole peaks (Shackleton rim ~0.83, de Gerlache rim ~0.73).
    While your task is LOS not illumination, the same raycasting gives
    horizon angles that should match Mazarico's figures within ±2°.

Public DEM product:
    PGDA Product 78 — LRO/LOLA south pole DEM, 5 m/pixel.
    Download: https://pgda.gsfc.nasa.gov/products/78
    Projection: polar stereographic, centered on south pole.
    Datum: MOON_ME, DE440.
"""

import numpy as np


def compute_horizon_angles(
    dem: np.ndarray,
    pixel_size_m: float,
    n_azimuths: int = 360,
) -> np.ndarray:
    """Compute horizon elevation angle in each azimuth direction for every DEM pixel.

    TODO (S1, Week 4):
        Algorithm (Mazarico 2011):
        1. For each pixel (i, j) and each azimuth direction φ:
           a. Cast a ray from (i, j) in direction φ.
           b. Sample the DEM along the ray at each pixel crossing.
           c. The horizon angle at φ is:
                  θ_horizon(φ) = max over all sampled pixels k of:
                      arctan((h[k] − h[i,j]) / r[k])
              where r[k] is the horizontal distance to pixel k.
           d. The point is in LOS for a source at azimuth φ if:
                  θ_source < θ_horizon(φ).

        Implementation tip: use np.linspace to step along rays; interpolate
        DEM heights at non-integer positions with scipy.ndimage.map_coordinates.

        Validation:
            Run on the PGDA-78 5-m DEM of the south pole.
            Extract horizon at Connecting Ridge (~89.5°S, 222°E).
            Should match Mazarico (2011) Fig. 5 horizon profile within ±1°.

    Parameters
    ----------
    dem : ndarray, shape (ny, nx)
        DEM elevation values in metres.
    pixel_size_m : float
        Ground sampling distance in metres (5 for PGDA-78).
    n_azimuths : int
        Number of azimuth directions to sample (default 360 → 1° resolution).

    Returns
    -------
    horizon_angles : ndarray, shape (ny, nx, n_azimuths)
        Horizon elevation angle in degrees for each pixel and azimuth.
    """
    raise NotImplementedError(
        "TODO (S1, Week 4): implement vectorised horizon raycasting. "
        "See Mazarico et al. (2011), doi:10.1016/j.icarus.2010.10.030"
    )


def los_mask_from_tx(
    dem: np.ndarray,
    pixel_size_m: float,
    tx_row: int,
    tx_col: int,
    h_tx_m: float,
    h_rx_m: float,
) -> np.ndarray:
    """Boolean LOS mask: True where the transmitter can see each DEM pixel.

    TODO (S1, Week 4):
        For a Tx at (tx_row, tx_col) with antenna height h_tx_m above terrain:
        1. For every pixel (i, j) with Rx antenna height h_rx_m above terrain:
           a. Cast a ray from Tx to (i, j).
           b. Check whether any intervening DEM pixel blocks the ray.
           c. Set los_mask[i, j] = True if no obstruction exists.

        This is equivalent to checking that the elevation angle from Tx to every
        point along the ray is ≥ the maximum terrain elevation angle from Tx.

        Vectorisation tip: compute all rays in a single loop over target pixels,
        but use precomputed horizon_angles from compute_horizon_angles() to avoid
        resampling the DEM for every pixel pair.

        Validation:
            From Connecting Ridge crest:
            - Shackleton crater floor (~5 km away, 4 km below) → NOT in LOS.
            - de Gerlache rim (~20 km away, same elevation) → IN LOS.
            Cross-check against LROC QuickMap visibility tool:
            https://quickmap.lroc.asu.edu/

    Parameters
    ----------
    dem : ndarray, shape (ny, nx)
    pixel_size_m : float
    tx_row, tx_col : int
        DEM pixel indices of the transmitter.
    h_tx_m : float
        Tx antenna height above terrain (metres).
    h_rx_m : float
        Rx antenna height above terrain (metres).

    Returns
    -------
    los_mask : ndarray bool, shape (ny, nx)
    """
    raise NotImplementedError(
        "TODO (S1, Week 4): implement Tx→all-pixels LOS mask. "
        "Validate against LROC QuickMap visibility at Connecting Ridge."
    )

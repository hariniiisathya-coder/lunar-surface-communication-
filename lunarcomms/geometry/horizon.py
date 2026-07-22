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
from scipy.ndimage import map_coordinates


def compute_horizon_angles(
    dem: np.ndarray,
    pixel_size_m: float,
    n_azimuths: int = 360,
    max_radius_m: float | None = None,
    observer_height_m: float = 0.0,
) -> np.ndarray:
    """Compute horizon elevation angle in each azimuth direction for every DEM pixel.

    Algorithm (Mazarico et al. 2011, doi:10.1016/j.icarus.2010.10.030):
    for each azimuth φ, march outward in steps of one pixel and track, per
    pixel, the running maximum of arctan((h[k] − h_obs) / r[k]). Vectorised
    over the whole grid: each radial step is ONE map_coordinates call sampling
    the entire DEM shifted by (k·sinφ, k·cosφ), so the cost is
    n_azimuths × n_steps grid interpolations, not a per-pixel Python loop.

    Rays leaving the DEM sample the edge value (mode="nearest"), which makes
    the horizon flat beyond the tile — fine for interior pixels, conservative
    near the border.

    Memory note: the (ny, nx, n_azimuths) float64 output is ~2.9 GB for a
    1000×1000 tile at 360 azimuths. For coverage work on large DEMs prefer
    los_mask_from_tx (single-Tx) or call this on a cropped tile / reduced
    n_azimuths.

    Parameters
    ----------
    dem : ndarray, shape (ny, nx)
        DEM elevation values in metres.
    pixel_size_m : float
        Ground sampling distance in metres (5 for PGDA-78).
    n_azimuths : int
        Number of azimuth directions to sample (default 360 → 1° resolution).
    max_radius_m : float, optional
        Maximum ray length. Default: the DEM diagonal (every pixel sees the
        full tile).
    observer_height_m : float
        Observer antenna height above the local terrain (default 0 = eye at
        the surface, the Mazarico convention).

    Returns
    -------
    horizon_angles : ndarray, shape (ny, nx, n_azimuths)
        Horizon elevation angle in degrees for each pixel and azimuth.
        Negative values mean the horizon is below the local horizontal
        (looking down off a ridge).
    """
    ny, nx = dem.shape
    if max_radius_m is None:
        max_radius_m = float(np.hypot(ny, nx)) * pixel_size_m
    n_steps = max(int(max_radius_m / pixel_size_m), 1)

    rows0, cols0 = np.mgrid[0:ny, 0:nx]
    h_obs = dem + observer_height_m

    azimuths = np.linspace(0.0, 2.0 * np.pi, n_azimuths, endpoint=False)
    out = np.full((ny, nx, n_azimuths), -90.0, dtype=float)

    for a_idx, phi in enumerate(azimuths):
        # Azimuth convention: 0 = grid north (-row), 90° = grid east (+col).
        drow = -np.cos(phi)
        dcol = np.sin(phi)
        best = np.full((ny, nx), -np.inf)
        for k in range(1, n_steps + 1):
            r_m = k * pixel_size_m
            rows = rows0 + k * drow
            cols = cols0 + k * dcol
            hk = map_coordinates(dem, [rows.ravel(), cols.ravel()],
                                 order=1, mode="nearest").reshape(ny, nx)
            np.maximum(best, np.arctan2(hk - h_obs, r_m), out=best)
        out[:, :, a_idx] = np.degrees(best)
    return out


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
    ny, nx = dem.shape
    mask = np.zeros((ny, nx), dtype=bool)
    tx_h = dem[tx_row, tx_col] + h_tx_m
    for i in range(ny):
        for j in range(nx):
            if i == tx_row and j == tx_col:
                mask[i, j] = True
                continue
            heights, dist = extract_profile(
                dem, tx_row, tx_col, i, j, pixel_size_m
            )
            rx_h = dem[i, j] + h_rx_m
            total = dist[-1]
            if total == 0 or len(heights) < 3:
                mask[i, j] = True
                continue
            ray = tx_h + (rx_h - tx_h) * (dist / total)
            clearance = ray[1:-1] - heights[1:-1]
            mask[i, j] = bool(np.all(clearance >= 0))
    return mask


def extract_profile(dem, tx_row, tx_col, rx_row, rx_col, pixel_size_m,
                    n_samples=None):
    """Sample DEM elevation along the straight pixel line Tx->Rx.

    Returns (heights, distances_m): elevation samples (m) and their horizontal
    ground distance from Tx (m). Bilinear interpolation via map_coordinates.
    """
    r0, c0 = float(tx_row), float(tx_col)
    r1, c1 = float(rx_row), float(rx_col)
    npix = int(np.hypot(r1 - r0, c1 - c0))
    if n_samples is None:
        n_samples = max(npix + 1, 2)
    rows = np.linspace(r0, r1, n_samples)
    cols = np.linspace(c0, c1, n_samples)
    heights = map_coordinates(dem, np.vstack([rows, cols]), order=1,
                              mode="nearest")
    seg = np.hypot(rows - r0, cols - c0) * pixel_size_m
    return heights, seg

"""
Spatial link budget: combine propagation models with LOS mask to produce
coverage maps stored as GeoTIFF.

**Student 1 (S1) — Week 5–6 implementation task.**
See TASKS.md § S1-W5.

Pipeline
--------
For each BTS candidate location and each Rx pixel in the DEM:
  1. Check LOS (horizon.los_mask_from_tx).
  2. If LOS: compute two-ray path loss along the surface path.
  3. If NOT LOS: compute Deygout diffraction loss over the terrain profile
     (extracted via pgda.extract_profile) added to FSPL.
  4. Compute link margin = EIRP − total_path_loss + G_rx − sensitivity.
  5. Write link_margin[row, col] to output GeoTIFF (same projection as DEM).

Expected output deliverable
----------------------------
Six GeoTIFF files:
    coverage_UHF_444MHz_los.tif      — LOS mask only
    coverage_UHF_444MHz_margin.tif   — link margin map in dB
    coverage_S_2500MHz_los.tif
    coverage_S_2500MHz_margin.tif
    coverage_Ka_27GHz_los.tif
    coverage_Ka_27GHz_margin.tif

Baseline comparison
--------------------
Edwards et al. (2023) NTRS 20220015268, Table IV:
    BTS at 30 m, NR band SFCGb1 (2503.5–2655 MHz), EIRP = 53 dBm,
    UE sensitivity = −106 dBm, 20 MHz NR, MCS-0.
    → Coverage radius ≈ 7–10 km (Friis only, no terrain).

Your map should show how terrain blockage reduces this to 2–4 km for
typical south-pole morphology, and how BTS height affects the result.
"""

import numpy as np
from pathlib import Path


def compute_coverage_map(
    dem: np.ndarray,
    dem_transform,
    dem_crs,
    tx_row: int,
    tx_col: int,
    h_tx_m: float,
    h_rx_m: float,
    freq_hz: float,
    eirp_dbm: float,
    rx_gain_dbi: float,
    sensitivity_dbm: float,
    rho: float = 1.50,
    use_diffraction: bool = True,
) -> np.ndarray:
    """Compute link margin map (dB) for a single BTS location.

    TODO (S1, Week 5):
        Implement the pipeline described in the module docstring.
        Use:
            lunarcomms.geometry.horizon.los_mask_from_tx()
            lunarcomms.propagation.two_ray.path_loss_db()
            lunarcomms.propagation.diffraction.deygout_loss_db()
            lunarcomms.propagation.friis.received_power_dbm()
            lunarcomms.io.pgda.extract_profile()

        For non-LOS pixels, the total path loss is:
            FSPL(d_3d, f) + deygout_loss_db(terrain_profile)

        where d_3d is the 3-D Euclidean distance (accounting for height diff).

    Parameters
    ----------
    dem : ndarray, shape (ny, nx)       Elevation in metres.
    dem_transform : affine.Affine       Rasterio transform (pixel→world).
    dem_crs : CRS                       Coordinate reference system.
    tx_row, tx_col : int                DEM pixel of BTS.
    h_tx_m, h_rx_m : float             Antenna heights above terrain (m).
    freq_hz : float                     Carrier frequency (Hz).
    eirp_dbm : float                    BTS EIRP (dBm).
    rx_gain_dbi : float                 UE antenna gain (dBi).
    sensitivity_dbm : float             UE sensitivity (dBm).
    rho : float                         Regolith density (g/cm³, default 1.50).
    use_diffraction : bool              Include Deygout loss for non-LOS pixels.

    Returns
    -------
    margin_map : ndarray, shape (ny, nx)   Link margin in dB (NaN = no signal).
    """
    raise NotImplementedError(
        "TODO (S1, Week 5): implement full spatial link budget pipeline. "
        "See docs/survey/03-rf-propagation.md for pipeline description."
    )


def save_coverage_geotiff(
    margin_map: np.ndarray,
    dem_transform,
    dem_crs,
    output_path: str | Path,
    band_label: str = "link_margin_dB",
) -> None:
    """Save coverage map to GeoTIFF.

    TODO (S1, Week 6):
        Use rasterio to write margin_map as a single-band Float32 GeoTIFF,
        preserving the DEM projection (polar stereographic) and transform.

        The output file must be openable in QGIS and have nodata = NaN.
        Check with: gdalinfo {output_path}

        Source: rasterio documentation — writing rasters:
        https://rasterio.readthedocs.io/en/latest/topics/writing.html

    Parameters
    ----------
    margin_map : ndarray, shape (ny, nx)
    dem_transform : affine.Affine
    dem_crs : CRS
    output_path : str or Path
    band_label : str   Used as raster band description.
    """
    raise NotImplementedError(
        "TODO (S1, Week 6): save GeoTIFF with rasterio. "
        "See https://rasterio.readthedocs.io/en/latest/topics/writing.html"
    )

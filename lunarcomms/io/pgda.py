"""
PGDA (Planetary Geodynamics Data Archive) product readers.

**Student 1 (S1) — Week 2–3 implementation task.**
See TASKS.md § S1-W2.

Public data sources
--------------------
PGDA Product 78 — LRO/LOLA South Pole DEM, 5 m/pixel:
    URL: https://pgda.gsfc.nasa.gov/products/78
    Files: SP_LOLA_DEM_05m.tif (~2 GB)
    Projection: Polar Stereographic (south), centered on −90° lat, 0° lon.
    Horizontal datum: MOON_ME, DE440.
    Vertical datum: Mean lunar radius = 1737.4 km.
    Reference: Barker, M. K. et al. (2016), doi:10.1016/j.icarus.2016.02.008

PGDA Product 81 — Illumination map (Mazarico et al. 2011):
    URL: https://pgda.gsfc.nasa.gov/products/81
    Files: SP_illumination_*.tif (average illumination fraction per pixel)
    Reference: Mazarico, E. et al. (2011), doi:10.1016/j.icarus.2010.10.030

PGDA Product 98 — Surface roughness at multiple baselines (Barker et al. 2025):
    URL: https://pgda.gsfc.nasa.gov/products/98
    Files: SP_roughness_*.tif (RMS slope at 5 m, 100 m, 1 km baselines)
    Reference: Barker, M. K. et al. (2025), doi:10.3847/PSJ/ad8a08

Siegler 2020 regolith density map (not a PGDA product):
    URL: https://zenodo.org/record/3834965
    Files: lunar_density_map.tif
    Reference: Siegler, M. A. et al. (2020), doi:10.1029/2020JE006405

Download all with:  python data/download_pgda.py
"""

from pathlib import Path
import numpy as np


def load_dem(
    tif_path: str | Path,
    clip_extent_km: float | None = None,
) -> tuple[np.ndarray, object, object]:
    """Load a PGDA GeoTIFF DEM and return (data, transform, crs).

    TODO (S1, Week 2):
        Use rasterio to open the GeoTIFF:
            import rasterio
            with rasterio.open(tif_path) as src:
                data = src.read(1).astype(float)
                transform = src.transform
                crs = src.crs

        Set nodata pixels (typically −9999 or the rasterio nodata value)
        to np.nan.

        If clip_extent_km is given, crop to a square of that half-width
        (in km) centred on the DEM centre using rasterio.windows.

        Sanity checks:
            - For PGDA-78 full tile: data.shape ≈ (119810, 119810) pixels
              (60 km radius / 5 m per pixel in each direction)
              You will typically work with a ~40 km clip around the south pole.
            - DEM values at the south pole region: −4000 to +4000 m.
            - Shackleton crater floor: ~−4200 m relative to mean sphere.
            - Connecting Ridge: ~−2000 to −1800 m.  (above surrounding plains)

        Source: rasterio documentation:
        https://rasterio.readthedocs.io/en/latest/quickstart.html

    Parameters
    ----------
    tif_path : str or Path
        Path to the GeoTIFF file.
    clip_extent_km : float or None
        If given, clip DEM to ±clip_extent_km around the centre.

    Returns
    -------
    data : ndarray, shape (ny, nx)   Elevation in metres, NaN for nodata.
    transform : affine.Affine        Pixel-to-world transform.
    crs : CRS                        Coordinate reference system.
    """
    raise NotImplementedError(
        "TODO (S1, Week 2): load PGDA GeoTIFF with rasterio. "
        "See https://rasterio.readthedocs.io/en/latest/quickstart.html"
    )


def extract_profile(
    dem: np.ndarray,
    pixel_size_m: float,
    start_row: int,
    start_col: int,
    end_row: int,
    end_col: int,
    n_samples: int = 1024,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract a terrain height profile along a straight path on the DEM.

    TODO (S1, Week 4):
        Use scipy.ndimage.map_coordinates to interpolate the DEM along a
        straight line from (start_row, start_col) to (end_row, end_col).

        Source: scipy.ndimage documentation:
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.map_coordinates.html

    Parameters
    ----------
    dem : ndarray, shape (ny, nx)
    pixel_size_m : float
    start_row, start_col : int    Transmitter DEM pixel.
    end_row, end_col : int        Receiver DEM pixel.
    n_samples : int               Number of samples along the profile.

    Returns
    -------
    heights_m : ndarray, shape (n_samples,)   Terrain heights in metres.
    distances_m : ndarray, shape (n_samples,) Cumulative distance along path.
    """
    raise NotImplementedError(
        "TODO (S1, Week 4): implement profile extraction with map_coordinates."
    )


def sample_density(
    density_tif_path: str | Path,
    rows: np.ndarray,
    cols: np.ndarray,
    dem_transform,
) -> np.ndarray:
    """Sample regolith bulk density at given DEM pixel locations.

    TODO (S1, Week 5):
        Load the Siegler (2020) density raster (Zenodo: https://zenodo.org/record/3834965)
        and reproject/resample it to the PGDA-78 pixel grid, then return
        density values at the requested (row, col) locations.

        Note: the Siegler density raster is at ~8 km resolution (LRO Diviner).
        You must resample to 5 m using rasterio.warp.reproject() or
        scipy.ndimage.zoom(). Use nearest-neighbour or bilinear interpolation.

    Parameters
    ----------
    density_tif_path : path to Siegler 2020 density GeoTIFF.
    rows, cols : ndarray   DEM pixel coordinates to sample.
    dem_transform : affine.Affine  DEM pixel-to-world transform.

    Returns
    -------
    density_gcm3 : ndarray   Bulk density in g/cm³ at each requested pixel.
    """
    raise NotImplementedError(
        "TODO (S1, Week 5): sample Siegler 2020 density raster. "
        "Source: https://zenodo.org/record/3834965"
    )

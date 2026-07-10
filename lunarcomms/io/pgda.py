"""PGDA product readers (ASCII-only build)."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


def load_dem(tif_path, clip_extent_km=None):
    """Load a PGDA GeoTIFF DEM and return (data, transform, crs).

    nodata pixels are converted to np.nan. If clip_extent_km is given,
    a square window of half-width clip_extent_km (in km) is read around
    the DEM centre instead of the full array.
    """
    tif_path = str(tif_path)
    with rasterio.open(tif_path) as src:
        if clip_extent_km is None:
            data = src.read(1).astype(float)
            transform = src.transform
            nodata = src.nodata
        else:
            # pixel size in metres (assumes square pixels)
            px_m = abs(src.transform.a)
            half_px = int((clip_extent_km * 1000.0) / px_m)
            cx, cy = src.width // 2, src.height // 2
            col_off = max(cx - half_px, 0)
            row_off = max(cy - half_px, 0)
            width = min(2 * half_px, src.width - col_off)
            height = min(2 * half_px, src.height - row_off)
            window = Window(col_off, row_off, width, height)
            data = src.read(1, window=window).astype(float)
            transform = src.window_transform(window)
            nodata = src.nodata
        crs = src.crs

    # mark nodata as NaN (handle both the file's nodata and the common -9999)
    if nodata is not None:
        data[data == nodata] = np.nan
    data[data <= -9000] = np.nan

    return data, transform, crs

# Auto-generated generator (corrected). Writes lunarcomms/io/pgda.py.
# Adds load_siegler_map + sample_loss_tangent_params (rasterio import lazy).
content = r'''"""PGDA product readers (ASCII-only build).

Contains:
  * load_dem              -- PGDA GeoTIFF DEM reader (unchanged).
  * load_siegler_map      -- read a Siegler (2020) raster .txt into (values,
                             lats, lons).
  * sample_loss_tangent_params -- sample a', b' at given lat/lon (the function
                             the two-ray spatial model calls).

Siegler map format (verified against the Zenodo files)
------------------------------------------------------
  * Dense raster, 720 rows x 1440 cols, whitespace-separated floats.
  * 0.25 deg / pixel. Row 0 ~ +89.875 deg lat (N), row 719 ~ -89.875 (S).
  * First and last columns are all-zero sentinels -> stripped (-> 720x1438).
  * a' is NEGATIVE (~ -4.56..0); b' ranges ~ -1.19..+0.18.
  * VALIDATED loss-tangent form: tan d = 10**(a' + f**b')  (see dielectric.py).
"""
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator

# rasterio is only needed by load_dem (GeoTIFF). Import it lazily so the
# Siegler a'/b' text-map functions work in environments without rasterio.

_N_ROWS = 720
_N_COLS_RAW = 1440
_DEG_PER_PIX = 0.25


def load_dem(tif_path, clip_extent_km=None):
    """Load a PGDA GeoTIFF DEM and return (data, transform, crs).

    nodata pixels are converted to np.nan. If clip_extent_km is given, a square
    window of half-width clip_extent_km (km) is read around the DEM centre.
    """
    tif_path = str(tif_path)
    import rasterio
    from rasterio.windows import Window
    with rasterio.open(tif_path) as src:
        if clip_extent_km is None:
            data = src.read(1).astype(float)
            transform = src.transform
            nodata = src.nodata
        else:
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
    if nodata is not None:
        data[data == nodata] = np.nan
    data[data <= -9000] = np.nan
    return data, transform, crs


# --------------------------------------------------------------------------
# Siegler a'/b' maps
# --------------------------------------------------------------------------
def _strip_sentinels(arr):
    """Remove the all-zero first and last columns (720x1440 -> 720x1438)."""
    if arr.shape != (_N_ROWS, _N_COLS_RAW):
        raise ValueError(f"unexpected Siegler map shape {arr.shape}")
    if not (np.allclose(arr[:, 0], 0.0) and np.allclose(arr[:, -1], 0.0)):
        raise ValueError("edge columns are not zero sentinels; inspect file")
    return arr[:, 1:-1]


def load_siegler_map(path):
    """Load one Siegler raster .txt -> (values 720x1438, lats, lons).

    lats descend from ~+89.875 to ~-89.875 (row 0 = north). lons are cell
    centres spanning 360 deg.
    """
    raw = np.loadtxt(str(path))
    vals = _strip_sentinels(raw)
    n_lat, n_lon = vals.shape
    lats = 90.0 - (np.arange(n_lat) + 0.5) * _DEG_PER_PIX
    lons = (np.arange(n_lon) + 0.5) * (360.0 / n_lon)
    return vals, lats, lons


def _build_interpolator(values, lats, lons, fill_value=np.nan):
    """Bilinear interpolator over (lat, lon), periodic in longitude.

    Returns sample(lat, lon) -> value (scalar or array). Only out-of-range
    LATITUDE returns fill_value; longitude wraps.
    """
    lats_inc = lats[::-1]
    vals_inc = values[::-1, :]
    n_lon = len(lons)
    dlon = 360.0 / n_lon
    lons_ext = np.concatenate(([lons[0] - dlon], lons, [lons[-1] + dlon]))
    vals_ext = np.concatenate([vals_inc[:, -1:], vals_inc, vals_inc[:, :1]], axis=1)
    interp = RegularGridInterpolator(
        (lats_inc, lons_ext), vals_ext,
        method="linear", bounds_error=False, fill_value=fill_value,
    )
    lon_lo = lons_ext[0]

    def sample(lat, lon):
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        lon_w = lon_lo + np.mod(lon - lon_lo, 360.0)
        pts = np.stack([np.ravel(lat), np.ravel(lon_w)], axis=-1)
        out = interp(pts)
        return out.reshape(np.shape(lat)) if np.ndim(lat) else float(out[0])

    return sample


# module-level cache so repeated sampling does not reload the files
_AB_CACHE = {}


def sample_loss_tangent_params(lat, lon, a_path, b_path):
    """Sample Siegler a', b' at (lat, lon). Returns (a_prime, b_prime).

    lat, lon may be scalars or arrays (broadcast together). a_path/b_path are
    the Zenodo 'Figure 11_Constant Loss Parameter_a'.txt' and
    'Figure 11_Frequency Exponent_b'.txt' files. Interpolators are cached per
    file pair.

    Feed the result into
        lunarcomms.regolith.dielectric.loss_tangent_ab(a', b', freq_ghz)
    to get the VALIDATED tan d = 10**(a' + f**b').
    """
    key = (str(a_path), str(b_path))
    if key not in _AB_CACHE:
        a_vals, lats, lons = load_siegler_map(a_path)
        b_vals, lats_b, lons_b = load_siegler_map(b_path)
        if a_vals.shape != b_vals.shape:
            raise ValueError("a'/b' map shape mismatch")
        _AB_CACHE[key] = (
            _build_interpolator(a_vals, lats, lons),
            _build_interpolator(b_vals, lats_b, lons_b),
        )
    sample_a, sample_b = _AB_CACHE[key]
    return sample_a(lat, lon), sample_b(lat, lon)
'''
import os
os.makedirs(os.path.dirname("lunarcomms/io/pgda.py"), exist_ok=True)
with open("lunarcomms/io/pgda.py", "w") as f:
    f.write(content)
print("Wrote lunarcomms/io/pgda.py (" + str(content.count("def ")) + " functions)")

"""
Spatial link budget: coverage maps as GeoTIFF. Student 1 (S1) -- Week 5-6.

Per Rx pixel: LOS (horizon.los_mask_from_tx) -> two_ray.path_loss_db;
NLOS -> friis.fspl_db(3-D dist) + diffraction.deygout_loss_db(profile from
horizon.extract_profile). margin = received_power_dbm - sensitivity.
"""
import numpy as np

from ..geometry.horizon import extract_profile, los_mask_from_tx
from ..propagation import diffraction, friis, two_ray


def compute_coverage_map(dem, dem_transform, dem_crs, tx_row, tx_col,
                         h_tx_m, h_rx_m, freq_hz, eirp_dbm, rx_gain_dbi,
                         sensitivity_dbm, rho=1.50, use_diffraction=True):
    """Link-margin map (dB) for a single BTS location. NaN where unreachable."""
    ny, nx = dem.shape
    px = abs(dem_transform[0]) if dem_transform is not None else 5.0
    margin = np.full((ny, nx), np.nan, dtype=float)

    los = los_mask_from_tx(dem, px, tx_row, tx_col, h_tx_m, h_rx_m)
    tx_elev = dem[tx_row, tx_col] + h_tx_m

    for i in range(ny):
        for j in range(nx):
            if i == tx_row and j == tx_col:
                margin[i, j] = eirp_dbm + rx_gain_dbi - sensitivity_dbm
                continue
            d_horiz = np.hypot(i - tx_row, j - tx_col) * px
            if d_horiz == 0:
                continue
            if los[i, j]:
                pl = float(two_ray.path_loss_db(d_horiz, h_tx_m, h_rx_m,
                                                freq_hz, rho))
            else:
                rx_elev = dem[i, j] + h_rx_m
                d3d = np.hypot(d_horiz, rx_elev - tx_elev)
                pl = float(friis.fspl_db(d3d, freq_hz))
                if use_diffraction:
                    h, dist = extract_profile(dem, tx_row, tx_col, i, j, px)
                    pl += float(diffraction.deygout_loss_db(
                        h, dist, h_tx_m, h_rx_m, freq_hz))
            prx = friis.received_power_dbm(eirp_dbm, pl, rx_gain_dbi)
            margin[i, j] = friis.link_margin_db(prx, sensitivity_dbm)
    return margin


def save_coverage_geotiff(margin_map, dem_transform, dem_crs, output_path,
                          band_label="link_margin_dB"):
    """Write margin_map as single-band Float32 GeoTIFF (nodata=NaN)."""
    import rasterio
    output_path = str(output_path)
    ny, nx = margin_map.shape
    with rasterio.open(
        output_path, "w", driver="GTiff", height=ny, width=nx, count=1,
        dtype="float32", crs=dem_crs, transform=dem_transform, nodata=float("nan"),
    ) as dst:
        dst.write(margin_map.astype("float32"), 1)
        dst.set_band_description(1, band_label)

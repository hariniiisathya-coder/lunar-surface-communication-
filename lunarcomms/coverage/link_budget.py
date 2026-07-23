"""
Spatial link budget: coverage maps as GeoTIFF. Student 1 (S1) -- Week 5-6.

Per Rx pixel: LOS (horizon.los_mask_from_tx) -> two_ray.path_loss_db;
NLOS -> friis.fspl_db(3-D dist) + diffraction.deygout_loss_db(profile from
horizon.extract_profile). margin = received_power_dbm - sensitivity.

Shadow fading: this model uses DETERMINISTIC terrain shadowing (the real-DEM
LOS mask plus Deygout diffraction) in place of the 3GPP TR 38.901 stochastic
log-normal shadow-fading term. On the airless Moon with a metre-scale DEM the
blockage is deterministic and site-specific, so we compute it rather than draw
it from a distribution -- state this explicitly when mapping onto the 38.901
correction table. Atmospheric attenuation is identically 0 dB (no atmosphere).
"""
import numpy as np

from ..geometry.horizon import (
    R_MOON_M,
    curvature_drop_m,
    extract_profile,
    los_mask_from_tx,
)
from ..propagation import diffraction, friis, two_ray


def compute_coverage_map(dem, dem_transform, dem_crs, tx_row, tx_col,
                         h_tx_m, h_rx_m, freq_hz, eirp_dbm, rx_gain_dbi,
                         sensitivity_dbm, rho=1.50, use_diffraction=True,
                         tx_pattern=None, rx_pattern=None,
                         sigma_h_m=0.0, roughness_model="ament", pol="v",
                         use_envelope=False,
                         curvature=True, planet_radius_m=R_MOON_M):
    """Link-margin map (dB) for a single BTS location. NaN where unreachable.

    tx_pattern, rx_pattern : optional lunarcomms.antenna.Pattern for the LOS
        two-ray reflected ray (per-ray weighting). Default None == isotropic.
    sigma_h_m, roughness_model : rough-surface reduction of the coherent LOS
        reflection (roughness.specular_factor). Default 0 == smooth.
    pol : LOS reflection polarization, "v" (default) or "h".
    use_envelope : if True, use the dual-slope local-mean model
        (two_ray.path_loss_envelope_db) for the LOS pixels instead of the exact
        coherent sum -- recommended for publication maps, since the exact nulls
        alias into concentric-ring moire below the DEM pixel. The envelope
        ignores per-ray antenna/roughness detail, so it is only used when no
        pattern/roughness is requested; otherwise the exact model is used.

    NOTE: antenna pattern / roughness / polarization currently modify the LOS
    two-ray pixels. NLOS pixels keep FSPL + Deygout with the scalar Rx gain;
    for pattern-weighted NLOS (diffracted ray launched toward the crater rim)
    use lunarcomms.export.taps.link_taps, which weights both LOS and NLOS.
    """
    ny, nx = dem.shape
    px = abs(dem_transform[0]) if dem_transform is not None else 5.0
    margin = np.full((ny, nx), np.nan, dtype=float)

    los = los_mask_from_tx(dem, px, tx_row, tx_col, h_tx_m, h_rx_m,
                           curvature=curvature, planet_radius_m=planet_radius_m)
    tx_elev = dem[tx_row, tx_col] + h_tx_m
    plain_los = (tx_pattern is None and rx_pattern is None
                 and not sigma_h_m and use_envelope)

    for i in range(ny):
        for j in range(nx):
            if i == tx_row and j == tx_col:
                margin[i, j] = eirp_dbm + rx_gain_dbi - sensitivity_dbm
                continue
            d_horiz = np.hypot(i - tx_row, j - tx_col) * px
            if d_horiz == 0:
                continue
            if los[i, j]:
                if plain_los:
                    pl = float(two_ray.path_loss_envelope_db(
                        d_horiz, h_tx_m, h_rx_m, freq_hz))
                else:
                    pl = float(two_ray.path_loss_db(
                        d_horiz, h_tx_m, h_rx_m, freq_hz, rho,
                        tx_pattern=tx_pattern, rx_pattern=rx_pattern,
                        sigma_h_m=sigma_h_m, roughness_model=roughness_model,
                        pol=pol))
            else:
                rx_elev = dem[i, j] + h_rx_m
                d3d = np.hypot(d_horiz, rx_elev - tx_elev)
                pl = float(friis.fspl_db(d3d, freq_hz))
                if use_diffraction:
                    h, dist = extract_profile(dem, tx_row, tx_col, i, j, px)
                    if curvature and dist[-1] > 0:
                        h = h + curvature_drop_m(dist, dist[-1], planet_radius_m)
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

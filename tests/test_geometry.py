"""
Tests for lunarcomms.geometry (frames, horizon).

Validation targets are cross-checked against:
  - JPL Horizons system: https://ssd.jpl.nasa.gov/horizons/
  - Mazarico et al. (2011) illumination fractions.
  - LROC QuickMap visibility tool: https://quickmap.lroc.asu.edu/

NOTE: Tests marked @pytest.mark.requires_kernels are skipped unless
SPICE kernels are present in data/kernels/. Run:
    python data/download_kernels.py
before running the full test suite.
"""

from pathlib import Path

import numpy as np
import pytest

_KERNELS_PRESENT = (
    Path("data/kernels/de440.bsp").exists()
    and Path("data/kernels/moon_de440_220930.tf").exists()
)
requires_kernels = pytest.mark.skipif(
    not _KERNELS_PRESENT,
    reason="SPICE kernels not found in data/kernels/. Run data/download_kernels.py."
)

from lunarcomms.geometry import frames, horizon  # noqa: E402

# ---------------------------------------------------------------------------
# Earth–Moon geometry (requires SPICE kernels)
# ---------------------------------------------------------------------------

class TestEarthMoonDistance:

    @requires_kernels
    def test_distance_in_physical_range(self):
        """Earth-Moon distance must be 356 500–406 700 km at any epoch.

        Physical bounds from orbital mechanics:
            Perigee (closest): ~356 500 km
            Apogee (farthest): ~406 700 km
        Source: NASA Moon Fact Sheet — https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
        """
        frames.load_kernels()
        import spiceypy as spice
        et = spice.str2et("2026-01-01T00:00:00")
        dist = frames.earth_moon_distance_km(et)
        assert 356_500 < dist < 406_700, (
            f"Earth-Moon distance {dist:.0f} km is outside physical bounds. "
            "Check your SPICE spkpos() call."
        )

    @requires_kernels
    def test_one_way_light_time(self):
        """One-way light time must be ~1.18–1.36 s.

        c = 299 792.458 km/s.
        At mean distance 384 400 km: OWLT = 1.282 s.
        """
        frames.load_kernels()
        import spiceypy as spice
        et = spice.str2et("2026-06-15T12:00:00")
        dist = frames.earth_moon_distance_km(et)
        owlt = dist / 299_792.458
        assert 1.18 < owlt < 1.36, (
            f"One-way light time {owlt:.3f} s out of expected range 1.18–1.36 s."
        )

    @requires_kernels
    def test_south_pole_earth_elevation(self):
        """Earth elevation from south pole must be 2–10° due to libration.

        The lunar rotation axis is tilted ~1.54° relative to the ecliptic.
        From the south pole, the Earth is always near the horizon (~5–7°)
        but varies with libration.
        Source: Mazarico et al. (2011), doi:10.1016/j.icarus.2010.10.030
        """
        frames.load_kernels()
        import spiceypy as spice
        et = spice.str2et("2026-06-15T12:00:00")
        el = frames.earth_elevation_angle_deg(0.0, -90.0, et)  # south pole
        assert 1.0 < el < 12.0, (
            f"Earth elevation from south pole should be ~5–7°, got {el:.2f}°. "
            "If negative, the terrain is blocking the view (not modelled here — "
            "this is the theoretical limb elevation only)."
        )


# ---------------------------------------------------------------------------
# Orbit geometry tests (no SPICE needed — purely geometric)
# ---------------------------------------------------------------------------

class TestHorizonMask:

    def test_flat_dem_all_in_los(self):
        """On a perfectly flat DEM, every point should be in LOS from the centre.

        On a flat surface with equal antenna heights, the only obstruction
        is Earth's curvature — but the Moon is also a sphere. However, for a
        small DEM patch (< 50 km), the chord effect is < 10 m, much smaller
        than typical antenna heights. Expect ~all pixels in LOS for h_tx ≥ 5 m.
        """
        flat_dem = np.zeros((101, 101), dtype=float)
        mask = horizon.los_mask_from_tx(
            flat_dem,
            pixel_size_m=100.0,
            tx_row=50, tx_col=50,
            h_tx_m=30.0, h_rx_m=2.0,
        )
        coverage = mask.mean()
        assert coverage > 0.95, (
            f"Flat DEM should give >95% LOS coverage, got {coverage:.2%}. "
            "Check that your raycasting is not falsely blocking flat terrain."
        )

    def test_wall_blocks_los(self):
        """A high wall between Tx and Rx should block LOS."""
        dem = np.zeros((101, 101), dtype=float)
        dem[:, 60] = 500.0  # 500-m wall at column 60
        mask = horizon.los_mask_from_tx(
            dem,
            pixel_size_m=100.0,
            tx_row=50, tx_col=50,
            h_tx_m=30.0, h_rx_m=2.0,
        )
        # Pixels to the right of the wall (col > 60) should NOT be in LOS
        right_of_wall = mask[:, 65:]
        assert right_of_wall.mean() < 0.1, (
            "Pixels behind a 500-m wall should mostly be blocked. "
            "Check that your horizon angle computation is correct."
        )

    def test_curvature_blocks_beyond_horizon(self):
        """A same-elevation point past the ~10 km mast horizon is NOT in LOS
        once the spherical-Moon bulge is included, but IS under flat-Earth.

        Flat 30 km DEM at 300 m/px; Tx 30 m mast at the left edge, targets at
        the same elevation along the row. Horizon for a 30 m mast on the Moon
        is sqrt(2 R h) ~ 10.2 km; the far edge (~30 km) must be blocked.
        """
        flat = np.zeros((3, 101), dtype=float)
        kw = dict(pixel_size_m=300.0, tx_row=1, tx_col=0, h_tx_m=30.0, h_rx_m=2.0)
        sphere = horizon.los_mask_from_tx(flat, curvature=True, **kw)
        flatE = horizon.los_mask_from_tx(flat, curvature=False, **kw)
        # far edge ~30 km: blocked on the sphere, visible on flat Earth
        assert not sphere[1, -1]
        assert flatE[1, -1]
        # curvature strictly reduces (or equals) coverage
        assert sphere.mean() < flatE.mean()

    def test_tx_always_sees_itself(self):
        """The Tx pixel should always be 'in LOS' with itself."""
        dem = np.zeros((51, 51), dtype=float)
        mask = horizon.los_mask_from_tx(
            dem, pixel_size_m=50.0,
            tx_row=25, tx_col=25,
            h_tx_m=30.0, h_rx_m=2.0,
        )
        assert mask[25, 25] is True or mask[25, 25] == 1, (
            "The Tx pixel must always be in LOS with itself."
        )

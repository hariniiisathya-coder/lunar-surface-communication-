"""diffraction_profile adds the spherical bulge used by the LOS mask and taps."""
import numpy as np

from lunarcomms.geometry.horizon import (R_MOON_M, diffraction_profile,
                                         extract_profile)


def test_bulge_added_at_midpoint():
    dem = np.zeros((3, 2001))
    h0, d = extract_profile(dem, 1, 0, 1, 2000, 5.0)
    h, d2 = diffraction_profile(dem, 1, 0, 1, 2000, 5.0)
    assert np.allclose(d, d2) and np.allclose(h0, 0.0)
    D = d[-1]
    assert h[0] == 0.0 and h[-1] == 0.0
    mid = len(h) // 2
    assert np.isclose(h[mid], d[mid] * (D - d[mid]) / (2 * R_MOON_M))
    assert np.isclose(h.max(), (D / 2) ** 2 / (2 * R_MOON_M), rtol=1e-3)  # ~7.2 m at 10 km


def test_curvature_off_is_extract_profile():
    dem = np.random.default_rng(0).normal(0, 5, (50, 50))
    h0, _ = extract_profile(dem, 3, 4, 40, 45, 5.0)
    h, _ = diffraction_profile(dem, 3, 4, 40, 45, 5.0, curvature=False)
    assert np.array_equal(h0, h)

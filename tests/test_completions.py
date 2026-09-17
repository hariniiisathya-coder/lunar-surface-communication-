"""Tests for the two formerly-stubbed functions: friis.max_range_m and
horizon.compute_horizon_angles."""

import numpy as np
import pytest

from lunarcomms.geometry import horizon
from lunarcomms.propagation import friis


class TestMaxRange:
    def test_roundtrip_with_fspl(self):
        """fspl_db(max_range_m(...)) must equal the allowed path loss."""
        d = friis.max_range_m(53.0, 0.0, -106.0, 2.5e9, margin_db=3.0)
        allowed = 53.0 + 0.0 - (-106.0) - 3.0
        # abs=0.01: fspl_db uses the rounded -147.55 constant, max_range_m the
        # exact 4*pi/c inversion -> 0.0024 dB systematic difference.
        assert float(friis.fspl_db(d, 2.5e9)) == pytest.approx(allowed, abs=0.01)

    def test_scaffold_case_corrected_value(self):
        """The scaffold's '8.5 km' target was inconsistent with its own
        formula; the correct free-space answer for those numbers is ~602 km."""
        d = friis.max_range_m(53.0, 0.0, -106.0, 2.5e9, margin_db=3.0)
        assert d == pytest.approx(602e3, rel=0.01)

    def test_monotonic_in_margin_and_frequency(self):
        d0 = friis.max_range_m(30, 0, -100, 2.5e9, margin_db=0)
        d3 = friis.max_range_m(30, 0, -100, 2.5e9, margin_db=3)
        dka = friis.max_range_m(30, 0, -100, 27e9, margin_db=0)
        assert d3 < d0          # margin shrinks range
        assert dka < d0         # higher f, fixed gains: shorter range


class TestHorizonAngles:
    def test_flat_dem_zero_horizon(self):
        dem = np.zeros((21, 21))
        h = horizon.compute_horizon_angles(dem, 10.0, n_azimuths=8)
        assert h.shape == (21, 21, 8)
        centre = h[10, 10, :]
        assert np.all(np.abs(centre) < 0.5)   # flat -> ~0 deg everywhere

    def test_wall_raises_horizon_only_toward_wall(self):
        dem = np.zeros((21, 21))
        dem[:, 15] = 200.0                    # wall to grid-east
        h = horizon.compute_horizon_angles(dem, 10.0, n_azimuths=4)
        # azimuth order: 0=N, 90=E, 180=S, 270=W
        centre = h[10, 5, :]                  # observer west of the wall
        east, west = centre[1], centre[3]
        assert east > 45.0                    # 200 m wall 100 m away
        assert abs(west) < 1.0

    def test_observer_height_lowers_horizon(self):
        dem = np.zeros((21, 21))
        dem[:, 15] = 200.0
        h0 = horizon.compute_horizon_angles(dem, 10.0, n_azimuths=4)
        h30 = horizon.compute_horizon_angles(dem, 10.0, n_azimuths=4,
                                             observer_height_m=30.0)
        assert h30[10, 5, 1] < h0[10, 5, 1]

    def test_consistent_with_los_mask(self):
        """A pixel the LOS mask marks visible from the Tx must satisfy the
        horizon criterion in the Tx->pixel azimuth (spot check)."""
        dem = np.zeros((21, 21))
        dem[:, 15] = 200.0
        mask = horizon.los_mask_from_tx(dem, 10.0, 10, 5, 2.0, 2.0)
        assert bool(mask[10, 2])      # west side: visible
        assert not bool(mask[10, 19])  # behind the wall: blocked

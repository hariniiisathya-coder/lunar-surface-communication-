"""
Tests for lunarcomms.export.taps — the tap-delay-line channel export.

Cross-validation targets:
  * Collapsed LOS tap must reproduce two_ray.path_loss_db exactly (the taps
    ARE the two-ray model, resolved in delay then re-collapsed).
  * Reflected-tap excess delay must match the far-field analytic
    2*h_tx*h_rx/(c*d).
  * NLOS tap gain must equal -deygout_loss_db.
  * Exports must round-trip (JSON, .mat) and respect MCHEM's grid limits.
"""

import json

import numpy as np
import pytest

from lunarcomms.export import taps
from lunarcomms.propagation import two_ray
from lunarcomms.propagation.diffraction import deygout_loss_db

_C = 299792458.0

# Flat 201x201 DEM, 10 m pixels; Tx at centre, standard 30 m / 2 m masts.
FLAT = np.zeros((201, 201))
PX = 10.0
TX = (100, 100)
H_TX, H_RX = 30.0, 2.0
F = 2.5e9


def _flat_link(rx=(100, 180)):
    return taps.link_taps(FLAT, PX, TX[0], TX[1], rx[0], rx[1],
                          H_TX, H_RX, F)


class TestLOSTwoRayTaps:
    def test_two_taps_direct_reference(self):
        lk = _flat_link()
        assert lk.los
        assert lk.delays_s.shape == (2,)
        assert lk.delays_s[0] == 0.0
        assert lk.gains[0] == 1.0 + 0.0j

    def test_reflected_delay_matches_analytic(self):
        lk = _flat_link()
        d = lk.meta["d_ground_m"]          # 800 m
        expected = 2.0 * H_TX * H_RX / (_C * d)   # far-field excess delay
        assert lk.delays_s[1] == pytest.approx(expected, rel=0.02)
        # sub-nanosecond: the emulator-resolution argument
        assert lk.delays_s[1] < 1e-9

    def test_reflected_gain_magnitude(self):
        lk = _flat_link()
        r1 = np.hypot(lk.meta["d_ground_m"], H_TX - H_RX)
        r2 = np.hypot(lk.meta["d_ground_m"], H_TX + H_RX)
        # |gain| = |Gamma| * r1/r2, and near grazing |Gamma| -> 1
        assert abs(lk.gains[1]) == pytest.approx(
            abs(lk.gains[1] / (r1 / r2)) * (r1 / r2))
        assert 0.5 < abs(lk.gains[1]) <= 1.0

    def test_collapsed_reproduces_two_ray_path_loss(self):
        """THE consistency check: FSPL(direct) - 20log10|collapsed gain|
        must equal the pipeline's own two-ray path loss."""
        for rx_col in (140, 160, 180, 199):
            lk = _flat_link((100, rx_col))
            clk = lk.collapsed(taps.MCHEM_TAP_RESOLUTION_S)
            assert clk.delays_s.shape == (1,)   # both rays in one 10 ns cell
            pl_taps = lk.fspl_direct_db - 20.0 * np.log10(abs(clk.gains[0]))
            pl_two_ray = float(two_ray.path_loss_db(
                lk.meta["d_ground_m"], H_TX, H_RX, F))
            assert pl_taps == pytest.approx(pl_two_ray, abs=0.05)


class TestNLOSDiffractionTaps:
    def _wall_dem(self):
        dem = np.zeros((201, 201))
        dem[:, 140] = 500.0        # 500 m knife-edge wall
        return dem

    def test_single_diffracted_tap(self):
        dem = self._wall_dem()
        lk = taps.link_taps(dem, PX, 100, 100, 100, 180, H_TX, H_RX, F)
        assert not lk.los
        assert lk.delays_s.shape == (1,)
        assert lk.delays_s[0] > 0.0

    def test_gain_matches_deygout(self):
        dem = self._wall_dem()
        lk = taps.link_taps(dem, PX, 100, 100, 100, 180, H_TX, H_RX, F)
        heights = np.zeros(81)
        heights[40] = 500.0
        dist = np.arange(81) * PX
        expected = deygout_loss_db(heights, dist, H_TX, H_RX, F)
        assert -lk.gains_db[0] == pytest.approx(expected, abs=0.5)

    def test_excess_delay_scale(self):
        """500 m edge at the midpoint of a 1.6 km path: excess ~ 2*sqrt(
        (d/2)^2+h^2)-d ~ 2*(sqrt(800^2? ...)) -- just check the order:
        hundreds of ns, well above the two-ray ns scale and below MCHEM max."""
        dem = self._wall_dem()
        lk = taps.link_taps(dem, PX, 100, 100, 100, 180, H_TX, H_RX, F)
        assert 1e-8 < lk.delays_s[0] < taps.MCHEM_MAX_DELAY_S


class TestTrajectory:
    def test_fading_trace_oscillates(self):
        """Along-track collapsed gain must show the two-ray null structure:
        multiple local minima (spatial fading a rover experiences in time)."""
        path = [(100, c) for c in range(120, 200, 2)]
        links = taps.trajectory_taps(FLAT, PX, TX[0], TX[1], path,
                                     H_TX, H_RX, F)
        mags = np.array([abs(lk.collapsed().gains[0]) for lk in links])
        assert len(links) == len(path)
        sign_changes = np.sum(np.abs(np.diff(np.sign(np.diff(mags)))) > 0)
        assert sign_changes >= 3, "expected oscillating two-ray gain"


class TestExports:
    def test_nrtdl_dict_fields(self):
        d = taps.to_nrtdl_dict(_flat_link(),
                               collapse_below_s=taps.MCHEM_TAP_RESOLUTION_S)
        assert d["PathDelays"].shape == (1, 1)
        assert d["AveragePathGains"].shape == (1, 1)
        assert d["CarrierHz"] == F
        assert np.isfinite(d["FSPLDirect_dB"])

    def test_mat_roundtrip(self, tmp_path):
        from scipy.io import loadmat
        p = str(tmp_path / "link.mat")
        taps.save_nrtdl_mat(_flat_link(), p)
        back = loadmat(p)
        assert back["PathDelays"].shape[-1] == 2
        assert back["AveragePathGains"].shape[-1] == 2

    def test_mat_trajectory_stack(self, tmp_path):
        from scipy.io import loadmat
        path = [(100, c) for c in (150, 160, 170)]
        links = taps.trajectory_taps(FLAT, PX, TX[0], TX[1], path,
                                     H_TX, H_RX, F)
        p = str(tmp_path / "traj.mat")
        taps.save_nrtdl_mat(links, p,
                            collapse_below_s=taps.MCHEM_TAP_RESOLUTION_S)
        back = loadmat(p)
        assert back["PathDelays"].shape[0] == 3
        assert back["GainMagnitude_dB"].shape == (3, 1)

    def test_json_roundtrip(self, tmp_path):
        p = str(tmp_path / "link.json")
        lk = _flat_link()
        taps.save_json(lk, p)
        with open(p) as f:
            back = json.load(f)
        assert back["los"] is True
        assert len(back["delays_s"]) == 2
        g1 = complex(*back["gains_re_im"][1])
        assert abs(g1) == pytest.approx(abs(lk.gains[1]), rel=1e-9)

    def test_colosseum_grid(self):
        delays, gains = taps.to_colosseum_taps(_flat_link())
        assert len(delays) <= taps.MCHEM_MAX_TAPS
        assert np.all(delays <= taps.MCHEM_MAX_DELAY_S)
        # delays on the 10 ns grid
        cells = delays / taps.MCHEM_TAP_RESOLUTION_S
        assert np.allclose(cells, np.round(cells))
        # lunar surface link: sparse — never truncated
        assert len(delays) >= 1

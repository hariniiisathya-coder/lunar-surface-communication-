"""
Tests for lunarcomms.export.lchem -- LCHEM MT-012 PDP export.

Anchored to the LCHEM user guide (USRP X410 RFNoC emulator):
  * complex-16 variant: <=16 complex taps, tau_max ~16.67 us; real-32: <=32
    real taps, tau_max ~8.33 us.
  * Delays in 10 ns ticks; Q1.15 complex/real coefficients (|c| < 1).
  * MT-011 shiftright: 0-12 bits coarse attenuation, 6.02 dB/bit.
  * Node ids 0=gNB, 2/4/6=UE1..3.
"""

import numpy as np
import pytest

from lunarcomms.export import lchem, taps

_TICK = 10e-9
FLAT = np.zeros((201, 201))


def _los():
    return taps.link_taps(FLAT, 10.0, 100, 100, 100, 180, 30, 2, 2.5e9)


def _nlos():
    dem = np.zeros((201, 201))
    dem[:, 140] = 500.0
    return taps.link_taps(dem, 10.0, 100, 100, 100, 180, 30, 2, 2.5e9)


class TestComplex16:
    def test_tap_and_delay_limits(self):
        p = lchem.to_lchem_pdp(_los(), mode="complex16")
        assert len(p["coeffs"]) <= 16
        assert len(p["delays_10ns"]) == len(p["coeffs"])
        max_ticks = int(round(16.67e-6 / _TICK))
        assert all(0 <= d <= max_ticks for d in p["delays_10ns"])

    def test_delays_are_integer_ticks(self):
        p = lchem.to_lchem_pdp(_nlos(), mode="complex16")
        assert all(isinstance(d, int) for d in p["delays_10ns"])
        # NLOS delay tick == round(excess delay / 10 ns)
        lk = _nlos()
        assert p["delays_10ns"][0] == int(round(lk.delays_s[0] / _TICK))

    def test_q115_range_and_quantization(self):
        p = lchem.to_lchem_pdp(_nlos(), mode="complex16")
        for c in p["coeffs"]:
            assert abs(c.real) < 1.0 and abs(c.imag) < 1.0
            # multiples of 1/32768
            assert c.real * 32768 == pytest.approx(round(c.real * 32768), abs=1e-6)

    def test_peak_scaled_to_headroom(self):
        p = lchem.to_lchem_pdp(_los(), mode="complex16", headroom=0.9)
        peak = max(abs(c) for c in p["coeffs"])
        assert peak == pytest.approx(0.9, abs=1.0 / 32768 * 2)

    def test_scale_split_reconstructs_absolute(self):
        # shiftright*6.02 + rf_residual == fspl_direct - norm_gain (the identity
        # that makes the emulated SNR correct).
        for lk in (_los(), _nlos()):
            p = lchem.to_lchem_pdp(lk, mode="complex16")
            applied = p["shiftright_bits"] * 20 * np.log10(2) + p["rf_residual_db"]
            assert applied == pytest.approx(
                p["fspl_direct_db"] - p["norm_gain_db"], abs=1e-6)

    def test_shiftright_in_range(self):
        for lk in (_los(), _nlos()):
            p = lchem.to_lchem_pdp(lk, mode="complex16")
            assert 0 <= p["shiftright_bits"] <= 12


class TestReal32:
    def test_real_coeffs_and_limits(self):
        p = lchem.to_lchem_pdp(_nlos(), mode="real32")
        assert len(p["coeffs"]) <= 32
        assert all(isinstance(c, float) for c in p["coeffs"])
        max_ticks = int(round(8.33e-6 / _TICK))
        assert all(0 <= d <= max_ticks for d in p["delays_10ns"])


class TestTrajectoryAndPack:
    def test_trajectory_one_frame_per_waypoint(self):
        path = [(100, c) for c in (150, 160, 170)]
        links = taps.trajectory_taps(FLAT, 10.0, 100, 100, path, 30, 2, 2.5e9)
        frames = lchem.trajectory_to_lchem(links, lchem.GNB, lchem.UE1)
        assert len(frames) == 3

    def test_mt012_tuple_shape(self):
        p = lchem.to_lchem_pdp(_los())
        tup = lchem.pdps_to_mt012_tuples([p])[0]
        assert tup[0] == lchem.GNB and tup[1] == lchem.UE1
        assert tup[2] == p["delays_10ns"] and tup[3] == p["coeffs"]

    def test_default_nodes(self):
        p = lchem.to_lchem_pdp(_los())
        assert (p["src_node"], p["dst_node"]) == (0, 2)  # gNB -> UE1

    def test_json_roundtrip(self, tmp_path):
        import json
        frames = [[lchem.to_lchem_pdp(_los())]]
        out = str(tmp_path / "cir.json")
        lchem.save_lchem_json(frames, out)
        with open(out) as f:
            back = json.load(f)
        assert back[0][0]["delays_10ns"] == frames[0][0]["delays_10ns"]

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            lchem.to_lchem_pdp(_los(), mode="complex8")

"""
Tests for lunarcomms.antenna — radiation patterns and per-ray weighting.

Expected values are anchored to the PRIMARY SOURCE, 3GPP TR 38.901 v17.0.0
Table 7.3-1 ("Radiation power pattern of a single antenna element"):
  * G_max      = 8 dBi
  * HPBW       = 65 deg (both cuts)   -> -3 dB at +/- HPBW/2 = +/- 32.5 deg
  * SLA_V/A_max= 30 dB  (front-to-back / side-lobe floor)
The per-ray weighting is checked against the two-ray geometry it plugs into,
and the isotropic default is checked to leave the pipeline exactly unchanged.
"""

import numpy as np
import pytest

from lunarcomms.antenna import (
    Isotropic,
    ThreeGPP38901Element,
    ray_elevations_deg,
    reflected_ray_weight,
)
from lunarcomms.propagation import two_ray

H_TX, H_RX, F = 30.0, 2.0, 2.5e9


class TestThreeGPP38901Pattern:
    def test_boresight_is_max_gain(self):
        # Table 7.3-1: gain at boresight = G_max = 8 dBi.
        el = ThreeGPP38901Element()
        assert el.gain_dbi(0.0, 0.0) == pytest.approx(8.0, abs=1e-9)

    def test_minus_3db_at_half_hpbw(self):
        # -3 dB at +/- HPBW/2 = +/- 32.5 deg in each cut (Table 7.3-1).
        el = ThreeGPP38901Element()
        assert el.gain_dbi(0.0, 32.5) == pytest.approx(5.0, abs=1e-6)
        assert el.gain_dbi(0.0, -32.5) == pytest.approx(5.0, abs=1e-6)
        assert el.gain_dbi(32.5, 0.0) == pytest.approx(5.0, abs=1e-6)

    def test_front_to_back_30db(self):
        # Back lobe (az=180) is >= 30 dB below boresight => <= -22 dBi.
        el = ThreeGPP38901Element()
        assert el.gain_dbi(180.0, 0.0) == pytest.approx(-22.0, abs=1e-6)
        assert el.gain_dbi(0.0, 0.0) - el.gain_dbi(180.0, 0.0) >= 30.0 - 1e-9

    def test_field_gain_is_sqrt_of_power(self):
        el = ThreeGPP38901Element()
        # field amplitude = 10**(dBi/20); power = field**2 = 10**(dBi/10).
        assert el.field_gain(0.0, 0.0) == pytest.approx(10.0 ** (8.0 / 20.0))

    def test_downtilt_shifts_boresight_down(self):
        # A 6 deg mechanical downtilt puts the 8 dBi peak at el = -6 deg.
        el = ThreeGPP38901Element(downtilt_deg=6.0)
        assert el.gain_dbi(0.0, -6.0) == pytest.approx(8.0, abs=1e-9)
        assert el.gain_dbi(0.0, -6.0) > el.gain_dbi(0.0, 0.0)

    def test_array_broadcast(self):
        el = ThreeGPP38901Element()
        out = el.gain_dbi(np.zeros(5), np.linspace(-32.5, 32.5, 5))
        assert out.shape == (5,)
        assert out.max() == pytest.approx(8.0, abs=1e-9)  # boresight in the middle


class TestIsotropicDefault:
    def test_constant_gain(self):
        iso = Isotropic()
        assert iso.field_gain(37.0, -12.0) == pytest.approx(1.0)
        assert iso.field_gain(180.0, 80.0) == pytest.approx(1.0)

    def test_weight_is_unity(self):
        # With isotropic patterns the reflected/direct ray ratio is exactly 1.
        w = reflected_ray_weight(800.0, H_TX, H_RX, Isotropic(), Isotropic())
        assert w == pytest.approx(1.0)

    def test_none_leaves_two_ray_unchanged(self):
        # The whole point of backward compatibility: no pattern == old result.
        d = np.linspace(100, 20000, 50)
        base = two_ray.path_loss_db(d, H_TX, H_RX, F)
        iso = two_ray.path_loss_db(d, H_TX, H_RX, F,
                                   tx_pattern=Isotropic(), rx_pattern=Isotropic())
        assert np.allclose(base, iso, atol=1e-9)


class TestPerRayGeometry:
    def test_reflected_ray_is_steeper_downward(self):
        # Reflected ray leaves the Tx more steeply downward than the direct ray
        # (it aims at the ground), so its elevation is more negative.
        _, _, el_tx_refl, _ = ray_elevations_deg(800.0, H_TX, H_RX)
        el_tx_dir, *_ = ray_elevations_deg(800.0, H_TX, H_RX)
        assert el_tx_refl < el_tx_dir < 0.0

    def test_directional_no_downtilt_attenuates_reflection(self):
        # Horizon-pointing directional element: the steeper reflected ray sits
        # further off boresight than the near-horizontal direct ray, so it is
        # attenuated -> weight < 1.
        bts = ThreeGPP38901Element()
        w = reflected_ray_weight(800.0, H_TX, H_RX, tx_pattern=bts)
        assert w < 1.0

    def test_downtilt_boosts_reflection_relative(self):
        # Tilting the beam down toward the ground reflection raises the
        # reflected ray's relative gain (monotonically, toward/above 1).
        w0 = reflected_ray_weight(800.0, H_TX, H_RX,
                                  tx_pattern=ThreeGPP38901Element(downtilt_deg=0))
        w_dt = reflected_ray_weight(800.0, H_TX, H_RX,
                                    tx_pattern=ThreeGPP38901Element(downtilt_deg=8))
        assert w_dt > w0


class TestTwoRayWithPattern:
    def test_pattern_changes_path_loss(self):
        # A directional downtilted mast must produce a different two-ray null
        # structure than isotropic at a distance inside the oscillation region.
        d = 500.0
        base = two_ray.path_loss_db(d, H_TX, H_RX, F)
        bts = ThreeGPP38901Element(downtilt_deg=8.0)
        pat = two_ray.path_loss_db(d, H_TX, H_RX, F, tx_pattern=bts)
        assert abs(pat - base) > 1e-3

    def test_matches_manual_weight_application(self):
        # The path loss with a pattern must equal the core model with the
        # analytically computed reflected-ray weight -- no hidden extra terms.
        d = 1234.0
        bts = ThreeGPP38901Element(downtilt_deg=5.0)
        ue = ThreeGPP38901Element()
        w = reflected_ray_weight(d, H_TX, H_RX, bts, ue)
        _, _, theta = two_ray._geometry(d, H_TX, H_RX)
        from lunarcomms.regolith.dielectric import fresnel_coefficients
        gamma_v, _ = fresnel_coefficients(1.50, F / 1e9, theta)
        expected = two_ray._two_ray_pl_from_gamma(d, H_TX, H_RX, F, gamma_v,
                                                  refl_weight=w)
        got = two_ray.path_loss_db(d, H_TX, H_RX, F,
                                   tx_pattern=bts, rx_pattern=ue)
        assert got == pytest.approx(expected, abs=1e-9)


class TestNLOSDiffractionWeighting:
    """The diffracted (Deygout) tap must also respond to the antenna pattern:
    it launches UP toward the dominant edge, not along the blocked direct line.
    """

    def _wall_link(self, tx_pattern=None):
        from lunarcomms.export import taps
        dem = np.zeros((201, 201))
        dem[:, 140] = 500.0  # 500 m knife-edge wall between Tx and Rx
        return taps.link_taps(dem, 10.0, 100, 100, 100, 180, H_TX, H_RX, F,
                              tx_pattern=tx_pattern)

    def test_isotropic_weight_is_unity(self):
        lk = self._wall_link()
        assert not lk.los
        assert lk.meta["antenna_weight"] == pytest.approx(1.0)

    def test_horizon_directional_attenuates_high_edge(self):
        # A horizon-pointing directional mast barely illuminates a 500 m rim
        # (edge is ~50 deg above boresight): weight << 1, tap gain drops.
        iso = self._wall_link()
        dir_ = self._wall_link(ThreeGPP38901Element())
        assert dir_.meta["antenna_weight"] < 1.0
        assert abs(dir_.gains[0]) < abs(iso.gains[0])

    def test_uptilt_toward_edge_boosts_relative_to_horizon(self):
        # Negative downtilt points the beam up toward the rim -> more NLOS gain.
        horizon = self._wall_link(ThreeGPP38901Element(downtilt_deg=0.0))
        uptilt = self._wall_link(ThreeGPP38901Element(downtilt_deg=-30.0))
        assert uptilt.meta["antenna_weight"] > horizon.meta["antenna_weight"]


class TestPolarization:
    def test_v_and_h_differ_at_steep_angle(self):
        # Short link / high mast => steep grazing angle => V (Brewster) != H.
        d = 50.0
        pv = two_ray.path_loss_db(d, H_TX, H_RX, F, pol="v")
        ph = two_ray.path_loss_db(d, H_TX, H_RX, F, pol="h")
        assert abs(pv - ph) > 0.5

    def test_v_and_h_converge_at_grazing(self):
        # Far field, near-grazing: both coefficients -> -1, choice immaterial.
        d = 20000.0
        pv = two_ray.path_loss_db(d, H_TX, H_RX, F, pol="v")
        ph = two_ray.path_loss_db(d, H_TX, H_RX, F, pol="h")
        assert abs(pv - ph) < 0.2

    def test_default_is_vertical(self):
        d = 500.0
        assert two_ray.path_loss_db(d, H_TX, H_RX, F) == pytest.approx(
            two_ray.path_loss_db(d, H_TX, H_RX, F, pol="v")
        )

    def test_invalid_pol_raises(self):
        with pytest.raises(ValueError):
            two_ray.path_loss_db(500.0, H_TX, H_RX, F, pol="circular")

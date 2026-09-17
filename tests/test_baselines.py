"""
Baseline-alignment gate: every physics module reproduces a CITED literature
value before we trust any derived result. This is the "align with baseline
first" contract -- run it in CI; if a refactor breaks a number here, the model
has drifted from its source.

Sources are named per assertion. Values are the primary-source numbers (or the
exact output of the cited closed-form equation), NOT hand-tuned guesses.
"""
import numpy as np
import pytest

from lunarcomms.antenna import ThreeGPP38901Element
from lunarcomms.export import taps
from lunarcomms.propagation import diffraction, friis, roughness, two_ray
from lunarcomms.regolith import dielectric


class TestFriisBaseline:
    """Friis (1946); ITU-R P.525; Edwards et al. (2023) NTRS 20220015268 T.III."""

    def test_fspl_1km_sband(self):
        assert friis.fspl_db(1000, 2.5e9) == pytest.approx(100.4, abs=0.3)

    def test_fspl_10km_sband_edwards(self):
        assert friis.fspl_db(10_000, 2.5e9) == pytest.approx(120.4, abs=0.3)

    def test_6db_per_octave(self):
        step = friis.fspl_db(2000, 2.5e9) - friis.fspl_db(1000, 2.5e9)
        assert step == pytest.approx(6.02, abs=0.02)


class TestTwoRayBaseline:
    """Rappaport (1996) ch.3: 1/d^4 far field, dual-slope breakpoint."""

    def test_far_field_40db_per_decade(self):
        pl1 = float(two_ray.path_loss_db(3e4, 30, 2, 2.5e9))
        pl2 = float(two_ray.path_loss_db(3e5, 30, 2, 2.5e9))
        assert (pl2 - pl1) == pytest.approx(40.0, abs=0.5)

    def test_envelope_continuous_at_breakpoint(self):
        dbp = np.pi * two_ray.breakpoint_distance(30, 2, 2.5e9)
        lo = two_ray.path_loss_envelope_db(dbp * 0.999, 30, 2, 2.5e9)
        hi = two_ray.path_loss_envelope_db(dbp * 1.001, 30, 2, 2.5e9)
        assert abs(lo - hi) < 0.05


class TestDiffractionBaseline:
    """ITU-R P.526-15 eq.14 knife-edge J(nu) (the implemented closed form)."""

    def test_j_at_zero(self):
        assert diffraction.knife_edge_loss_db(0.0) == pytest.approx(6.02, abs=0.1)

    def test_j_at_one(self):
        assert diffraction.knife_edge_loss_db(1.0) == pytest.approx(13.93, abs=0.1)

    def test_j_at_2p4(self):
        # eq.14 output at nu=2.4 is 20.54 dB (the exact Fresnel value ~20.6);
        # this pins the implemented approximation, not a wishful round number.
        assert diffraction.knife_edge_loss_db(2.4) == pytest.approx(20.54, abs=0.1)

    def test_j_clamped_below_threshold(self):
        assert diffraction.knife_edge_loss_db(-1.0) == 0.0


class TestDielectricBaseline:
    """Olhoeft & Strangway (1975); Siegler et al. (2020)."""

    def test_permittivity_surface(self):
        assert dielectric.permittivity(1.50) == pytest.approx(2.658, abs=0.01)

    def test_loss_tangent_full_siegler_form(self):
        assert dielectric.loss_tangent(1.50, 2.5) == pytest.approx(0.00554, abs=5e-4)

    def test_fresnel_grazing_tends_to_minus_one(self):
        gv, gh = dielectric.fresnel_coefficients(1.5, 2.5, np.deg2rad(0.05))
        assert abs(gv) == pytest.approx(1.0, abs=0.02)
        assert abs(gh) == pytest.approx(1.0, abs=0.02)
        assert gv.real < -0.9


class TestRoughnessBaseline:
    """Ament (1953) / Beckmann-Spizzichino (1963)."""

    def test_smooth_is_unity(self):
        assert roughness.specular_factor(0.0, 140e9, np.deg2rad(20)) == 1.0

    def test_matches_ament_closed_form(self):
        ra = roughness.rayleigh_parameter(0.03, 27e9, np.deg2rad(8))
        assert roughness.specular_factor(0.03, 27e9, np.deg2rad(8)) == pytest.approx(
            np.exp(-ra ** 2 / 2), abs=1e-9
        )


class TestAntennaBaseline:
    """3GPP TR 38.901 Table 7.3-1."""

    def test_boresight_8dbi(self):
        assert ThreeGPP38901Element().gain_dbi(0, 0) == pytest.approx(8.0, abs=1e-6)

    def test_minus_3db_at_half_hpbw(self):
        assert ThreeGPP38901Element().gain_dbi(0, 32.5) == pytest.approx(5.0, abs=1e-4)


class TestCrossModelConsistency:
    """The exported channel IS the coverage model, resolved in delay."""

    def test_collapsed_tap_equals_two_ray(self):
        flat = np.zeros((201, 201))
        worst = 0.0
        for rc in (140, 160, 180, 199):
            lk = taps.link_taps(flat, 10.0, 100, 100, 100, rc, 30, 2, 2.5e9)
            clk = lk.collapsed(taps.MCHEM_TAP_RESOLUTION_S)
            pl_tap = lk.fspl_direct_db - 20 * np.log10(abs(clk.gains[0]))
            pl_2r = float(two_ray.path_loss_db(lk.meta["d_ground_m"], 30, 2, 2.5e9))
            worst = max(worst, abs(pl_tap - pl_2r))
        assert worst < 0.05

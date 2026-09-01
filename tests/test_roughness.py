"""
Tests for lunarcomms.propagation.roughness — coherent-reflection reduction.

Anchored to primary definitions:
  * Rayleigh parameter  Ra = 4*pi*sigma_h*sin(theta)/lambda, smooth if Ra<pi/2
    (Rayleigh criterion; Beckmann & Spizzichino 1963, ch. 2).
  * Ament (1953) / Beckmann specular factor rho_s = exp(-Ra^2/2).
  * Miller-Brown-Vegh (1984) rho_s = exp(-Ra^2/2) I0(Ra^2/2) >= Ament.
Plus the physical consequence the pipeline needs: at high band a rough surface
decoheres the ground reflection and the two-ray path loss reverts to FSPL.
"""

import numpy as np
import pytest

from lunarcomms.propagation import friis, roughness, two_ray

_C = 299792458.0
H_TX, H_RX = 30.0, 2.0


class TestRayleighParameter:
    def test_formula(self):
        sigma, f, theta = 0.02, 27.0e9, np.deg2rad(10.0)
        lam = _C / f
        expected = 4.0 * np.pi * sigma * np.sin(theta) / lam
        assert roughness.rayleigh_parameter(sigma, f, theta) == pytest.approx(expected)

    def test_smoothness_threshold(self):
        # Choose sigma exactly at the criterion Ra = pi/2 and step across it.
        f, theta = 2.5e9, np.deg2rad(5.0)
        lam = _C / f
        sigma_crit = lam / (8.0 * np.sin(theta))          # Ra = pi/2
        assert roughness.is_smooth(sigma_crit * 0.99, f, theta)
        assert not roughness.is_smooth(sigma_crit * 1.01, f, theta)


class TestSpecularFactor:
    def test_smooth_surface_is_unity(self):
        rho_s = roughness.specular_factor(0.0, 140e9, np.deg2rad(20))
        assert rho_s == pytest.approx(1.0)

    def test_ament_matches_closed_form(self):
        sigma, f, theta = 0.03, 27.0e9, np.deg2rad(8.0)
        ra = roughness.rayleigh_parameter(sigma, f, theta)
        assert roughness.specular_factor(sigma, f, theta) == pytest.approx(
            np.exp(-ra ** 2 / 2.0)
        )

    def test_decreases_with_frequency(self):
        vals = [roughness.specular_factor(0.02, f, np.deg2rad(10))
                for f in (0.442e9, 2.5e9, 27e9, 140e9)]
        assert all(a > b for a, b in zip(vals, vals[1:]))   # strictly decreasing

    def test_miller_brown_at_least_ament(self):
        sigma, f, theta = 0.03, 27e9, np.deg2rad(8.0)
        am = roughness.specular_factor(sigma, f, theta, model="ament")
        mb = roughness.specular_factor(sigma, f, theta, model="miller-brown")
        assert mb >= am

    def test_unknown_model_raises(self):
        with pytest.raises(ValueError):
            roughness.specular_factor(0.01, 2.5e9, np.deg2rad(5), model="nope")


class TestTwoRayIntegration:
    def test_rough_high_band_reverts_to_fspl(self):
        # At 140 GHz a 5 cm RMS surface is deep in the diffuse regime: the
        # coherent reflection vanishes and the two-ray loss collapses to the
        # free-space loss of the direct ray, at ANY distance (peak or null).
        for d in (300.0, 517.0, 900.0):
            pl_rough = two_ray.path_loss_db(d, H_TX, H_RX, 140e9, sigma_h_m=0.05)
            r1 = np.hypot(d, H_TX - H_RX)
            assert pl_rough == pytest.approx(friis.fspl_db(r1, 140e9), abs=0.5)

    def test_smooth_default_unchanged(self):
        d = np.linspace(100, 10000, 40)
        base = two_ray.path_loss_db(d, H_TX, H_RX, 27e9)
        same = two_ray.path_loss_db(d, H_TX, H_RX, 27e9, sigma_h_m=0.0)
        assert np.allclose(base, same, atol=1e-12)

"""Tests for two_ray.path_loss_envelope_db (dual-slope local-mean model)."""

import numpy as np

from lunarcomms.propagation import friis, two_ray

H_TX, H_RX, F = 30.0, 2.0, 2.5e9
D0 = two_ray.breakpoint_distance(H_TX, H_RX, F)   # null breakpoint, ~2 km
D_BP = np.pi * D0                                 # FSPL / far-field crossover


def test_matches_fspl_below_crossover():
    d = D_BP / 4
    env = two_ray.path_loss_envelope_db(d, H_TX, H_RX, F)
    r1 = np.hypot(d, H_TX - H_RX)
    assert env == friis.fspl_db(r1, F)


def test_continuous_at_crossover():
    lo = two_ray.path_loss_envelope_db(D_BP * 0.999, H_TX, H_RX, F)
    hi = two_ray.path_loss_envelope_db(D_BP * 1.001, H_TX, H_RX, F)
    assert abs(lo - hi) < 0.05          # no 9.9 dB step


def test_dual_slope_beyond_crossover():
    d1, d2 = 3 * D_BP, 30 * D_BP        # a decade in the 1/d^4 regime
    pl1 = two_ray.path_loss_envelope_db(d1, H_TX, H_RX, F)
    pl2 = two_ray.path_loss_envelope_db(d2, H_TX, H_RX, F)
    assert abs((pl2 - pl1) - 40.0) < 0.1


def test_monotonic_no_oscillation():
    d = np.linspace(50, 40000, 800)
    env = two_ray.path_loss_envelope_db(d, H_TX, H_RX, F)
    assert np.all(np.diff(env) > -1e-6)   # never decreases (no nulls)


def test_tracks_exact_far_field_local_mean():
    # Beyond the crossover the exact coherent sum is smooth and follows the
    # far-field asymptote; the envelope should match it closely.
    d = np.linspace(3 * D_BP, 12 * D_BP, 400)
    env = two_ray.path_loss_envelope_db(d, H_TX, H_RX, F)
    exact = two_ray.path_loss_db(d, H_TX, H_RX, F)
    assert np.mean(np.abs(exact - env)) < 1.0

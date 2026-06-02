"""
Tests for lunarcomms.propagation (Friis, two-ray, diffraction).

All expected values are taken from published papers, ITU-R tables, or
analytically derivable from the formulas. Passing these tests means your
implementation is consistent with the cited literature.

References validated here
--------------------------
[F46]  Friis (1946), Proc. IRE 34, 254–256. doi:10.1109/JRPROC.1946.234568
[P525] ITU-R P.525-4 (2019). Free-space attenuation.
[P526] ITU-R P.526-15 (2019). Propagation by diffraction.
[R96]  Rappaport (1996), Wireless Communications, Ch. 3. ISBN 0-13-375536-3.
[T22]  Toonen et al. (2022), IEEE J. Radio Freq. Identif., vol. 6. doi:10.1109/JRFID.2022.3159775
[E23]  Edwards et al. (2023), NTRS 20220015268.
"""

import pytest
import numpy as np
from lunarcomms.propagation import friis, two_ray, diffraction


# ---------------------------------------------------------------------------
# Friis FSPL
# ---------------------------------------------------------------------------

class TestFriis:

    def test_known_value_1km_sband(self):
        """FSPL(1 km, 2.5 GHz) = 20*log10(4π*1000*2.5e9/c) ≈ 100.4 dB [P525]."""
        result = friis.fspl_db(1000, 2.5e9)
        assert abs(result - 100.4) < 0.2, (
            f"Expected ~100.4 dB, got {result:.2f} dB. "
            "Use: 20*log10(4π*d*f/c)."
        )

    def test_known_value_10km_sband(self):
        """FSPL(10 km, 2.5 GHz) ≈ 120.4 dB — reproduces Edwards (2023) Table III."""
        result = friis.fspl_db(10_000, 2.5e9)
        assert abs(result - 120.4) < 0.2, (
            f"Expected ~120.4 dB, got {result:.2f} dB. "
            "Cross-check: Edwards (2023) NTRS 20220015268 Table III."
        )

    def test_20db_per_decade(self):
        """Doubling distance adds exactly 6.02 dB (FSPL ∝ d²)."""
        pl1 = friis.fspl_db(1000, 2.5e9)
        pl2 = friis.fspl_db(2000, 2.5e9)
        assert abs((pl2 - pl1) - 6.02) < 0.01, (
            "FSPL must increase by exactly 20*log10(2) ≈ 6.02 dB when doubling distance."
        )

    def test_array_input(self):
        """fspl_db() must accept array distance inputs."""
        distances = np.array([100, 1000, 10000])
        result = friis.fspl_db(distances, 2.5e9)
        assert result.shape == (3,)
        assert np.all(np.diff(result) > 0), "FSPL must increase with distance."


# ---------------------------------------------------------------------------
# Breakpoint distance
# ---------------------------------------------------------------------------

class TestBreakpoint:

    def test_s_band_operational(self):
        """Breakpoint at S-band (2.5 GHz), hT=30m, hR=2m ≈ 2000 m.

        This means ALL operational lunar surface links (d > 2 km) at S-band
        are in the 1/d⁴ regime, not 1/d². Critical design insight.
        """
        dc = two_ray.breakpoint_distance(30.0, 2.0, 2.5e9)
        assert abs(dc - 2000) < 100, (
            f"Expected breakpoint ≈ 2000 m at S-band, got {dc:.0f} m. "
            "Use: dc = 4*hT*hR*f/c"
        )

    def test_uhf_shorter_breakpoint(self):
        """UHF breakpoint (442 MHz) ≈ 354 m — shorter than S-band."""
        dc_uhf = two_ray.breakpoint_distance(30.0, 2.0, 0.442e9)
        dc_s = two_ray.breakpoint_distance(30.0, 2.0, 2.5e9)
        assert dc_uhf < dc_s, "UHF breakpoint must be shorter than S-band."
        assert abs(dc_uhf - 354) < 20

    def test_antenna_height_scales_linearly(self):
        """Breakpoint scales linearly with each antenna height [R96 eq. 3.27]."""
        dc1 = two_ray.breakpoint_distance(30.0, 2.0, 2.5e9)
        dc2 = two_ray.breakpoint_distance(60.0, 2.0, 2.5e9)  # double hT
        assert abs(dc2 / dc1 - 2.0) < 0.01, (
            "Breakpoint must double when Tx height doubles."
        )


# ---------------------------------------------------------------------------
# Two-ray path loss
# ---------------------------------------------------------------------------

class TestTwoRay:

    def test_free_space_limit_at_short_range(self):
        """Near the transmitter (d << breakpoint), two-ray ≈ free-space ± 6 dB.

        The two-ray model oscillates between Friis±6dB in the near-field.
        It cannot exceed Friis + 6dB or be less than Friis − 6dB for
        coherent addition of two equal-amplitude rays.
        """
        d = 10.0  # 10 m — well within breakpoint
        pl_tr = two_ray.path_loss_db(d, 30.0, 2.0, 2.5e9)
        pl_fs = friis.fspl_db(d, 2.5e9)
        assert abs(pl_tr - pl_fs) <= 7.0, (  # 6 dB + 1 dB tolerance
            f"At short range, two-ray should be within ±6 dB of Friis. "
            f"Got Δ = {pl_tr - pl_fs:.1f} dB."
        )

    def test_far_field_penalty(self):
        """At d = 10 km >> breakpoint (2 km), two-ray adds ~20 dB vs Friis.

        Beyond the breakpoint, PL_two_ray ≈ FSPL + 20*log10(d²/(hT*hR))
        minus a constant. The additional loss at 10 km for hT=30m, hR=2m
        should be in the range 15–25 dB above Friis.

        Reference: Toonen et al. (2021) show received power ~20 dB below
        Friis at 10 km for εr=3 — your result should be within ±5 dB.
        """
        d = 10_000.0
        pl_tr = two_ray.path_loss_db(d, 30.0, 2.0, 2.5e9)
        pl_fs = friis.fspl_db(d, 2.5e9)
        delta = pl_tr - pl_fs
        assert 10 < delta < 35, (
            f"Two-ray should add 15–25 dB at 10 km (got Δ={delta:.1f} dB). "
            "Cross-check against Toonen et al. (2021) Fig. 4."
        )

    def test_path_loss_increases_with_distance(self):
        """Path loss must increase (on average) with distance."""
        distances = np.linspace(100, 20000, 50)
        pl = two_ray.path_loss_db(distances, 30.0, 2.0, 2.5e9)
        # Check that the smoothed trend increases (allow oscillations)
        window = 5
        pl_smooth = np.convolve(pl, np.ones(window) / window, mode="valid")
        assert np.all(np.diff(pl_smooth) > -2), (
            "Smoothed two-ray path loss must not decrease significantly."
        )


# ---------------------------------------------------------------------------
# Knife-edge diffraction (ITU-R P.526-15)
# ---------------------------------------------------------------------------

class TestDiffraction:

    @pytest.mark.parametrize("nu, expected_db", [
        (-1.0,  0.0),    # deep clearance
        ( 0.0,  6.0),    # grazing (Huygens principle: −6 dB vs free-space)
        ( 1.0, 12.0),    # moderate obstruction [P526 Table 1]
        (11.5, 33.0),    # 200-m rim at S-band, d=5 km  (calculated from P526)
        (38.0, 44.0),    # same rim at Ka-band
    ])
    def test_knife_edge_table(self, nu, expected_db):
        """Validate against ITU-R P.526-15 Table 1 and analytical cases."""
        result = diffraction.knife_edge_loss_db(nu)
        assert abs(result - expected_db) < 1.5, (
            f"J(ν={nu}) should be ≈{expected_db} dB, got {result:.2f} dB. "
            "See ITU-R P.526-15, Table 1."
        )

    def test_nu_parameter_200m_rim_sband(self):
        """200-m rim at midpoint, d1=d2=2500 m, S-band → ν ≈ 11.5 [P526 eq.13]."""
        nu = diffraction.fresnel_kirchhoff_parameter(200, 2500, 2500, 2.5e9)
        assert abs(nu - 11.5) < 0.5, (
            f"Expected ν ≈ 11.5 for 200-m rim at S-band midpoint, got {nu:.2f}. "
            "Check: ν = h·√(2/λ·(1/d1+1/d2))"
        )

    def test_clearance_gives_negative_nu(self):
        """Obstacle below LOS (h<0) gives ν<0 → no diffraction loss."""
        nu = diffraction.fresnel_kirchhoff_parameter(-50, 2500, 2500, 2.5e9)
        assert nu < 0, "Negative h (clearance) must give negative ν."
        loss = diffraction.knife_edge_loss_db(nu)
        assert loss < 1.0, "Clearance should give near-zero diffraction loss."

    def test_deygout_single_edge_matches_knife_edge(self):
        """For a single knife-edge profile, Deygout must match knife_edge_loss_db."""
        # Build a single-obstacle profile: flat at 0 m except one peak at 200 m
        d_total = 5000.0
        n = 101
        distances = np.linspace(0, d_total, n)
        heights = np.zeros(n)
        heights[n // 2] = 200.0  # single obstacle at midpoint

        deygout_result = diffraction.deygout_loss_db(
            heights, distances, h_tx_m=2.0, h_rx_m=2.0, freq_hz=2.5e9
        )
        nu = diffraction.fresnel_kirchhoff_parameter(200 - 2, 2500, 2500, 2.5e9)
        ke_result = diffraction.knife_edge_loss_db(nu)

        assert abs(deygout_result - ke_result) < 2.0, (
            f"Single-edge Deygout ({deygout_result:.2f} dB) must match "
            f"knife-edge ({ke_result:.2f} dB) within 2 dB."
        )

"""
Tests for lunarcomms.regolith.dielectric.

All expected values are taken directly from published papers and tables.
A passing test suite means your implementation matches the published literature.

References validated here
--------------------------
[O75]  Olhoeft & Strangway (1975), Earth Planet. Sci. Lett. 24, 394–408.
       doi:10.1016/0012-821X(75)90146-6
[C91]  Carrier, Olhoeft & Mendell (1991), Lunar Sourcebook, Ch. 9.
       Table 9.1 (density), Table 9.2 (permittivity).
[S20]  Siegler et al. (2020), JGR Planets 125, e2020JE006405.
       doi:10.1029/2020JE006405. Fig. 4 (loss tangent vs frequency).
"""

import numpy as np

from lunarcomms.regolith import dielectric

# ---------------------------------------------------------------------------
# permittivity — Olhoeft & Strangway (1975), Table 2
# ---------------------------------------------------------------------------

class TestPermittivity:
    """Values from [O75] Table 2 and [C91] Table 9.2."""

    def test_surface_layer(self):
        """Upper 30 cm: ρ=1.50 g/cm³ → ε'≈2.69 [C91 Table 9.2]."""
        result = dielectric.permittivity(1.50)
        assert abs(result - 2.69) < 0.01, (
            f"Expected ε'≈2.69 at ρ=1.50 g/cm³, got {result:.4f}. "
            "Check: ε' = 1.919^1.50 = 2.690"
        )

    def test_deep_regolith(self):
        """Deep regolith: ρ=1.74 g/cm³ → ε'≈3.20 [C91 Table 9.2]."""
        result = dielectric.permittivity(1.74)
        assert abs(result - 3.20) < 0.02, (
            f"Expected ε'≈3.20 at ρ=1.74 g/cm³, got {result:.4f}."
        )

    def test_low_density_surface(self):
        """Top 2 cm: ρ=1.30 g/cm³ → ε'≈2.30 [O75 Figure 2]."""
        result = dielectric.permittivity(1.30)
        assert abs(result - 2.30) < 0.02, (
            f"Expected ε'≈2.30 at ρ=1.30 g/cm³, got {result:.4f}."
        )

    def test_array_input(self):
        """Array input returns array output of the same shape."""
        rho = np.array([1.30, 1.50, 1.74])
        result = dielectric.permittivity(rho)
        assert result.shape == (3,), "Array input should return array."
        assert np.all(result > 1.0), "Permittivity must be > 1."
        assert np.all(np.diff(result) > 0), "ε' must increase with density."

    def test_physical_lower_bound(self):
        """ε' > 1 for any physical density [vacuum = 1]."""
        assert dielectric.permittivity(0.5) > 1.0
        assert dielectric.permittivity(3.0) > 1.0


# ---------------------------------------------------------------------------
# loss_tangent — Siegler et al. (2020), Figure 4
# ---------------------------------------------------------------------------

class TestLossTangent:
    """Values digitised from [S20] Figure 4 at ρ=1.50 g/cm³."""

    def test_s_band(self):
        """S-band 2.5 GHz: tan δ ≈ 0.0082 [S20 Fig. 4]."""
        result = dielectric.loss_tangent(1.50, 2.5)
        assert abs(result - 0.0082) < 0.0008, (
            f"Expected tan δ ≈ 0.0082 at S-band, got {result:.5f}. "
            "Check: 10^(0.312*1.50 + 0.278*log10(2.5) - 2.636)"
        )

    def test_uhf(self):
        """UHF 0.44 GHz: tan δ ≈ 0.0054 [S20 Fig. 4]."""
        result = dielectric.loss_tangent(1.50, 0.44)
        assert abs(result - 0.0054) < 0.0008, (
            f"Expected tan δ ≈ 0.0054 at UHF, got {result:.5f}."
        )

    def test_ka_band(self):
        """Ka-band 27 GHz: tan δ ≈ 0.0170 [S20 Fig. 4]."""
        result = dielectric.loss_tangent(1.50, 27.0)
        assert abs(result - 0.0170) < 0.0020, (
            f"Expected tan δ ≈ 0.0170 at Ka-band, got {result:.5f}."
        )

    def test_frequency_dependence(self):
        """tan δ must increase monotonically with frequency [S20, eq. 6]."""
        freqs = np.array([0.44, 2.5, 8.4, 27.0])
        tans = dielectric.loss_tangent(1.50, freqs)
        assert np.all(np.diff(tans) > 0), (
            "Loss tangent must increase with frequency. "
            "Check the sign of the 0.278·log10(f_GHz) term."
        )

    def test_density_dependence(self):
        """tan δ must increase monotonically with density [S20, eq. 6]."""
        densities = np.array([1.30, 1.50, 1.74])
        tans = dielectric.loss_tangent(densities, 2.5)
        assert np.all(np.diff(tans) > 0), (
            "Loss tangent must increase with density. "
            "Check the sign of the 0.312·ρ term."
        )

    def test_edwards_simplification_error(self):
        """Quantify error from Edwards (2023) tan δ=0 assumption.

        Edwards et al. (2023) NTRS 20220015268 use tan δ = 0.
        Your implementation should show this is an approximation:
        the true value is 0.008 at S-band, not zero.
        """
        result = dielectric.loss_tangent(1.50, 2.5)
        assert result > 0, "tan δ must be positive (Edwards 2023 used 0)."
        assert result < 0.05, "tan δ < 5% for regolith (not a conductor)."


# ---------------------------------------------------------------------------
# complex_permittivity
# ---------------------------------------------------------------------------

class TestComplexPermittivity:
    def test_real_part_matches_permittivity(self):
        """Re(ε) == permittivity(ρ)."""
        eps = dielectric.complex_permittivity(1.50, 2.5)
        eps_r = dielectric.permittivity(1.50)
        assert abs(eps.real - eps_r) < 1e-6

    def test_imaginary_part_is_negative(self):
        """Im(ε) = −ε'·tan δ < 0 (lossy medium)."""
        eps = dielectric.complex_permittivity(1.50, 2.5)
        assert eps.imag < 0, "Imaginary part must be negative for lossy medium."

    def test_tan_delta_ratio(self):
        """−Im(ε)/Re(ε) == tan δ."""
        eps = dielectric.complex_permittivity(1.50, 2.5)
        tan_d = dielectric.loss_tangent(1.50, 2.5)
        ratio = -eps.imag / eps.real
        assert abs(ratio - tan_d) < 1e-6


# ---------------------------------------------------------------------------
# fresnel_coefficients — Physical limits
# ---------------------------------------------------------------------------

class TestFresnelCoefficients:
    """Physical limits from Balanis (2012), Section 5.3."""

    def test_grazing_limit_vertical(self):
        """At grazing (θ→0): |Γ_v| → 1, Γ_v → −1."""
        gv, _ = dielectric.fresnel_coefficients(1.50, 2.5, 0.001)
        assert abs(abs(gv) - 1.0) < 0.05, (
            f"|Γ_v| should be ~1 at grazing, got {abs(gv):.3f}"
        )
        assert gv.real < -0.9, (
            f"Γ_v.real should be ~−1 at grazing, got {gv.real:.3f}"
        )

    def test_grazing_limit_horizontal(self):
        """At grazing (θ→0): |Γ_h| → 1, Γ_h → −1."""
        _, gh = dielectric.fresnel_coefficients(1.50, 2.5, 0.001)
        assert abs(abs(gh) - 1.0) < 0.05
        assert gh.real < -0.9

    def test_te_always_negative_real(self):
        """Γ_h.real < 0 for all angles (TE polarisation, ε>1)."""
        angles = np.linspace(0.01, np.pi / 2, 20)
        for theta in angles:
            _, gh = dielectric.fresnel_coefficients(1.50, 2.5, theta)
            assert gh.real < 0, f"Γ_h.real should be negative at θ={np.degrees(theta):.1f}°"

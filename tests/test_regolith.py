"""
Tests for lunarcomms.regolith.dielectric.

Expected values are anchored to PRIMARY SOURCES:
  * Permittivity: eps' = 1.919**rho (Olhoeft & Strangway 1975), computed
    directly -- no digitised/approximate values.
  * Loss tangent: the Siegler et al. (2020) form tan d = 10**(a' + f**b'),
    with a', b' from Siegler Table 1 (regions of their Figure 10), validated
    against Siegler Figure 8 integrated-loss maps to ~5%.
"""
import numpy as np

from lunarcomms.regolith import dielectric

S20_TABLE1 = {
    "Mare Serenitatis": (-3.351, -0.0811),
    "Mare Tranquillitatis": (-3.208, -0.0422),
    "Farside highlands": (-3.745, 0.0663),
}


class TestPermittivity:
    def test_surface_layer(self):
        result = dielectric.permittivity(1.50)
        assert abs(result - 2.658) < 0.01, (
            f"Expected eps'=2.658 at rho=1.50, got {result:.4f}."
        )

    def test_deep_regolith(self):
        result = dielectric.permittivity(1.74)
        assert abs(result - 3.108) < 0.02, (
            f"Expected eps'=3.108 at rho=1.74, got {result:.4f}."
        )

    def test_low_density_surface(self):
        result = dielectric.permittivity(1.30)
        assert abs(result - 2.333) < 0.02, (
            f"Expected eps'=2.333 at rho=1.30, got {result:.4f}."
        )

    def test_array_input(self):
        rho = np.array([1.30, 1.50, 1.74])
        result = dielectric.permittivity(rho)
        assert result.shape == (3,)
        assert np.all(result > 1.0)
        assert np.all(np.diff(result) > 0)

    def test_physical_lower_bound(self):
        assert dielectric.permittivity(0.5) > 1.0
        assert dielectric.permittivity(3.0) > 1.0

    def test_density_dependence(self):
        densities = np.array([1.30, 1.50, 1.74])
        eps = dielectric.permittivity(densities)
        assert np.all(np.diff(eps) > 0)


class TestLossTangentAB:
    def test_mare_serenitatis_sband(self):
        a, b = S20_TABLE1["Mare Serenitatis"]
        result = float(dielectric.loss_tangent_ab(a, b, 2.5))
        assert abs(result - 0.00378) < 0.0005, f"got {result:.5f}"

    def test_mare_tranquillitatis_sband(self):
        a, b = S20_TABLE1["Mare Tranquillitatis"]
        result = float(dielectric.loss_tangent_ab(a, b, 2.5))
        assert abs(result - 0.00568) < 0.0005, f"got {result:.5f}"

    def test_farside_highlands_sband(self):
        a, b = S20_TABLE1["Farside highlands"]
        result = float(dielectric.loss_tangent_ab(a, b, 2.5))
        assert abs(result - 0.00208) < 0.0005, f"got {result:.5f}"

    def test_all_regions_physical_range(self):
        for name, (a, b) in S20_TABLE1.items():
            for f in (0.44, 2.5, 27.0):
                td = float(dielectric.loss_tangent_ab(a, b, f))
                assert 0.0005 < td < 0.05, f"{name} at {f} GHz: {td:.5f}"

    def test_mare_falls_with_frequency(self):
        freqs = np.array([0.44, 2.5, 8.4, 27.0])
        for name in ("Mare Serenitatis", "Mare Tranquillitatis"):
            a, b = S20_TABLE1[name]
            td = dielectric.loss_tangent_ab(a, b, freqs)
            assert np.all(np.diff(td) < 0), f"{name}: expected falling tan d."

    def test_highlands_rises_with_frequency(self):
        freqs = np.array([0.44, 2.5, 8.4, 27.0])
        a, b = S20_TABLE1["Farside highlands"]
        td = dielectric.loss_tangent_ab(a, b, freqs)
        assert np.all(np.diff(td) > 0)

    def test_clamp_catches_uhf_extrapolation(self):
        raw = float(dielectric.loss_tangent_ab(-1.93, -1.19, 0.442, clamp=False))
        assert raw > 1.0
        clamped = float(dielectric.loss_tangent_ab(-1.93, -1.19, 0.442, clamp=True))
        assert clamped <= dielectric.TAN_DELTA_CEILING + 1e-9

    def test_array_frequency(self):
        a, b = S20_TABLE1["Mare Serenitatis"]
        td = dielectric.loss_tangent_ab(a, b, np.array([0.44, 2.5, 27.0]))
        assert td.shape == (3,)


class TestLossTangentBaseline:
    def test_baseline_physical(self):
        for f in (0.44, 2.5, 27.0):
            td = dielectric.loss_tangent(1.50, f)
            assert 0 < td < 0.05

    def test_baseline_array_frequency(self):
        freqs = np.array([0.44, 2.5, 27.0])
        td = dielectric.loss_tangent(1.50, freqs)
        assert np.asarray(td).shape == (3,)

    def test_edwards_simplification_error(self):
        result = dielectric.loss_tangent(1.50, 2.5)
        assert result > 0
        assert result < 0.05


class TestComplexPermittivity:
    def test_real_part_matches_permittivity(self):
        eps = dielectric.complex_permittivity(1.50, 2.5)
        assert abs(eps.real - dielectric.permittivity(1.50)) < 1e-6

    def test_imaginary_part_is_negative(self):
        eps = dielectric.complex_permittivity(1.50, 2.5)
        assert eps.imag < 0

    def test_tan_delta_ratio(self):
        eps = dielectric.complex_permittivity(1.50, 2.5)
        tan_d = dielectric.loss_tangent(1.50, 2.5)
        assert abs(-eps.imag / eps.real - tan_d) < 1e-6


class TestFresnelCoefficients:
    def test_grazing_limit_vertical(self):
        gv, _ = dielectric.fresnel_coefficients(1.50, 2.5, 0.001)
        assert abs(abs(gv) - 1.0) < 0.05
        assert gv.real < -0.9

    def test_grazing_limit_horizontal(self):
        _, gh = dielectric.fresnel_coefficients(1.50, 2.5, 0.001)
        assert abs(abs(gh) - 1.0) < 0.05
        assert gh.real < -0.9

    def test_te_always_negative_real(self):
        angles = np.linspace(0.01, np.pi / 2, 20)
        for theta in angles:
            _, gh = dielectric.fresnel_coefficients(1.50, 2.5, theta)
            assert gh.real < 0

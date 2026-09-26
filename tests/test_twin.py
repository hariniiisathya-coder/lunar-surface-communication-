"""
Tests for lunarcomms.twin (LunarTwin) -- the non-Sionna stages: DEM->mesh,
regolith material, scene XML, and the Sionna-CIR->LinkTaps conversion that
feeds the same LCHEM MT-012 export as LunaCov. The ray-trace itself needs a
Sionna install and is not exercised here.
"""

import numpy as np
import pytest

from lunarcomms.export import lchem
from lunarcomms.twin import (
    LunarTwin,
    dem_to_mesh,
    regolith_material_params,
    sionna_cir_to_linktaps,
)


class TestMesh:
    def test_counts(self):
        dem = np.zeros((10, 12))
        v, f = dem_to_mesh(dem, 5.0, stride=1, curvature=False)
        assert v.shape == (10 * 12, 3)
        assert f.shape == (2 * 9 * 11, 3)

    def test_stride_decimates(self):
        dem = np.zeros((20, 20))
        v, _ = dem_to_mesh(dem, 5.0, stride=4)
        assert v.shape[0] == 5 * 5   # every 4th sample

    def test_curvature_lowers_edges(self):
        dem = np.zeros((21, 21))
        v, _ = dem_to_mesh(dem, 100.0, stride=1, curvature=True)
        z = v[:, 2].reshape(21, 21)
        assert z[10, 10] == pytest.approx(0.0, abs=1e-6)   # center unchanged
        assert z[0, 0] < -0.5                              # corner pulled down


class TestMaterial:
    def test_permittivity_and_conductivity(self):
        p = regolith_material_params(1.50, 2.5)
        assert p["relative_permittivity"] == pytest.approx(2.658, abs=0.01)
        # sigma = 2*pi*f*eps0*eps'*tan_delta
        assert p["conductivity"] == pytest.approx(0.00205, rel=0.1)
        assert p["conductivity"] > 0

    def test_spatial_loss_tangent_path(self):
        # a', b' path (Shackleton-like) gives a larger loss tangent -> larger sigma
        base = regolith_material_params(1.50, 2.5)
        spat = regolith_material_params(1.50, 2.5, a_prime=-2.627, b_prime=-0.122)
        assert spat["conductivity"] > base["conductivity"]


class TestCirConversion:
    def test_reference_is_strongest_and_relative(self):
        a = np.array([1.0 + 0j, 0.3 + 0.1j])
        tau = np.array([1.0e-6, 1.2e-6])
        lk = sionna_cir_to_linktaps(a, tau, 2.5e9)
        assert lk.fspl_direct_db == pytest.approx(0.0, abs=1e-9)  # |a_ref|=1
        assert lk.delays_s[0] == pytest.approx(0.0)               # excess delay
        assert lk.delays_s[1] == pytest.approx(0.2e-6, abs=1e-12)
        assert abs(lk.gains[0]) == pytest.approx(1.0)

    def test_feeds_lchem_export(self):
        a = np.array([0.01 + 0j, 0.004 - 0.002j])
        tau = np.array([1.0e-6, 1.05e-6])
        lk = sionna_cir_to_linktaps(a, tau, 2.5e9)
        pdp = lchem.to_lchem_pdp(lk, mode="complex16")
        assert len(pdp["coeffs"]) <= 16
        assert 0 <= pdp["shiftright_bits"] <= 12
        assert all(abs(c) < 1.0 for c in pdp["coeffs"])

    def test_empty_cir(self):
        lk = sionna_cir_to_linktaps(np.array([]), np.array([]), 2.5e9)
        assert lk.gains.shape == (1,)


class TestBuild:
    def test_build_writes_scene(self, tmp_path):
        dem = np.random.default_rng(0).standard_normal((30, 30)) * 20
        tw = LunarTwin(dem, pixel_size_m=5.0)
        out = tw.build(str(tmp_path / "scene"), stride=2)
        assert out["n_verts"] == 15 * 15
        with open(out["xml"]) as f:
            xml = f.read()
        assert "terrain.ply" in xml
        with open(out["ply"]) as f:
            assert f.readline().strip() == "ply"

    def test_load_without_sionna_raises_cleanly(self, tmp_path):
        dem = np.zeros((10, 10))
        tw = LunarTwin(dem, 5.0)
        tw.build(str(tmp_path / "s"), stride=1)
        with pytest.raises((ImportError, ModuleNotFoundError)):
            tw.load(2.5e9)   # no Sionna installed

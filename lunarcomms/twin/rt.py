"""
LunarTwin: a Sionna RT scene over a real LOLA tile, as a second CIR source that
feeds the same LCHEM MT-012 export as LunaCov.

Structure mirrors BostonTwin (wineslab/boston_twin): a georeferenced mesh plus
a radio material, assembled into a Sionna scene, ray-traced to per-link CIRs.
Here the mesh is terrain (twin.mesh) and the material is regolith
(twin.materials). The Sionna calls are isolated in :meth:`LunarTwin.load` and
:meth:`LunarTwin.link_cir`; everything else runs without Sionna.

STATUS: the CIR->LinkTaps->LCHEM seam is validated against sionna-rt 2.1.0 on
an A100 (Sionna PathSolver over a built-in scene -> sionna_cir_to_linktaps ->
lchem.to_lchem_pdp). :meth:`link_cir` targets the Sionna RT 1.x/2.x PathSolver
API. Loading a custom LOLA-terrain mesh (:meth:`build` -> :meth:`load`) may need
the scene XML adapted to your Sionna version's radio-material format; the mesh,
material, scene-XML writer, and CIR conversion are exercised by tests.
"""

from __future__ import annotations

import os

import numpy as np

from ..export.taps import LinkTaps
from .mesh import R_MOON_M, dem_to_mesh, write_ply

_C = 299792458.0
# Sionna requires the shape's BSDF to carry an id that follows its radio-material
# naming (an itu_* built-in), which we override with the regolith RadioMaterial
# in load(). Validated against sionna-rt 2.1.0.
_MITSUBA_SCENE = """<scene version="2.1.0">
  <shape type="ply" id="terrain">
    <string name="filename" value="{ply}"/>
    <bsdf type="diffuse" id="{material_id}"/>
  </shape>
</scene>
"""


def write_mitsuba_scene(ply_filename: str, out_xml: str,
                        material_id: str = "itu_concrete") -> None:
    """Minimal Sionna-loadable scene XML referencing the terrain PLY. The BSDF
    id is a built-in ITU placeholder so ``load_scene`` accepts it;
    :meth:`LunarTwin.load` then overrides it with the regolith RadioMaterial."""
    with open(out_xml, "w") as f:
        f.write(_MITSUBA_SCENE.format(ply=ply_filename, material_id=material_id))


def sionna_cir_to_linktaps(a, tau, freq_hz: float, meta: dict | None = None,
                           mag_floor: float = 1e-12) -> LinkTaps:
    """Convert a Sionna CIR (complex amplitudes ``a``, delays ``tau`` in s) into
    a LunaCov :class:`LinkTaps`, using the same convention as LunaCov: gains are
    relative to the reference (direct/strongest) path and ``fspl_direct_db``
    carries the absolute scale. This makes Sionna CIRs interchangeable with
    LunaCov's through ``lchem.to_lchem_pdp``.
    """
    a = np.atleast_1d(np.asarray(a, dtype=complex)).ravel()
    tau = np.atleast_1d(np.asarray(tau, dtype=float)).ravel()
    if a.size == 0:
        return LinkTaps(np.array([0.0]), np.array([0.0 + 0.0j]), False, 0.0,
                        {**(meta or {}), "source": "sionna-rt"})
    ref = int(np.argmax(np.abs(a)))          # reference path = strongest
    a_ref = a[ref] if abs(a[ref]) > mag_floor else complex(mag_floor)
    fspl_direct_db = float(-20.0 * np.log10(max(abs(a_ref), mag_floor)))
    gains = a / a_ref
    delays = tau - tau[ref]
    order = np.argsort(delays)
    los = bool(delays[order][0] <= 0 or ref == int(np.argmin(tau)))
    return LinkTaps(delays_s=delays[order], gains=gains[order], los=los,
                    fspl_direct_db=fspl_direct_db,
                    meta={**(meta or {}), "freq_hz": float(freq_hz),
                          "source": "sionna-rt", "n_paths": int(a.size)})


class LunarTwin:
    """A Sionna RT digital twin of a LOLA tile.

    Non-Sionna: :meth:`build` (DEM -> mesh + PLY + scene XML). Sionna:
    :meth:`load` (scene + regolith material) and :meth:`link_cir` /
    :meth:`link_taps` (ray trace -> CIR -> LinkTaps).
    """

    def __init__(self, dem: np.ndarray, pixel_size_m: float, rho: float = 1.50,
                 planet_radius_m: float = R_MOON_M):
        self.dem = np.asarray(dem, dtype=float)
        self.px = float(pixel_size_m)
        self.rho = float(rho)
        self.R = float(planet_radius_m)
        self.scene = None
        self._xml = None

    def build(self, out_dir: str, stride: int = 2, curvature: bool = True):
        """DEM -> mesh -> terrain.ply + scene.xml in ``out_dir`` (no Sionna)."""
        os.makedirs(out_dir, exist_ok=True)
        verts, faces = dem_to_mesh(self.dem, self.px, stride=stride,
                                   curvature=curvature, planet_radius_m=self.R)
        ply = os.path.join(out_dir, "terrain.ply")
        write_ply(verts, faces, ply)
        self._xml = os.path.join(out_dir, "scene.xml")
        write_mitsuba_scene("terrain.ply", self._xml)
        return {"ply": ply, "xml": self._xml, "n_verts": len(verts),
                "n_faces": len(faces)}

    def load(self, freq_hz: float, a_prime=None, b_prime=None):
        """Load the scene into Sionna and assign the regolith material (lazy)."""
        from sionna.rt import PlanarArray, load_scene

        from .materials import build_radio_material
        if self._xml is None:
            raise RuntimeError("call build() first")
        scene = load_scene(self._xml)
        scene.frequency = float(freq_hz)
        mat = build_radio_material("regolith", self.rho, freq_hz / 1e9,
                                   a_prime, b_prime)
        for obj in scene.objects.values():
            obj.radio_material = mat
        scene.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                     polarization="V")
        scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                     polarization="V")
        self.scene = scene
        return scene

    def link_cir(self, tx_xyz, rx_xyz, max_depth: int = 3,
                 diffraction: bool = True, scattering: bool = False):
        """Ray trace one Tx->Rx link -> (a, tau). Requires :meth:`load` (lazy).

        Uses the Sionna RT 1.x/2.x ``PathSolver`` (validated against sionna-rt
        2.1.0). ``diffraction`` enables both wedge and edge diffraction;
        ``scattering`` enables diffuse reflection.
        """
        from sionna.rt import PathSolver, Receiver, Transmitter
        if self.scene is None:
            raise RuntimeError("call load(freq_hz) first")
        try:                                    # replace any prior endpoints
            self.scene.remove("tx")
            self.scene.remove("rx")
        except Exception:
            pass
        self.scene.add(Transmitter("tx", position=list(map(float, tx_xyz))))
        self.scene.add(Receiver("rx", position=list(map(float, rx_xyz))))
        paths = PathSolver()(self.scene, max_depth=max_depth, los=True,
                             specular_reflection=True, diffraction=diffraction,
                             edge_diffraction=diffraction,
                             diffuse_reflection=scattering)
        a, tau = paths.cir(out_type="numpy", normalize_delays=False)
        a = np.asarray(a)
        tau = np.asarray(tau)
        if a.ndim and a.shape[-1] == 1:         # drop the num_time_steps axis
            a = a[..., 0]
        return a.ravel(), tau.ravel()

    def link_taps(self, tx_xyz, rx_xyz, freq_hz: float, **kw) -> LinkTaps:
        """Ray-traced LinkTaps for one link (feeds lchem.to_lchem_pdp)."""
        a, tau = self.link_cir(tx_xyz, rx_xyz, **kw)
        return sionna_cir_to_linktaps(a, tau, freq_hz,
                                      meta={"tx": tuple(tx_xyz),
                                            "rx": tuple(rx_xyz)})


__all__ = ["LunarTwin", "write_mitsuba_scene", "sionna_cir_to_linktaps"]

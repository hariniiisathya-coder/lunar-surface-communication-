"""
lunarcomms.twin
===============
LunarTwin -- a Sionna RT digital twin of a LOLA tile, as a SECOND CIR source
that feeds the same LCHEM MT-012 export as the analytic LunaCov pipeline.

Structure follows BostonTwin (wineslab/boston_twin), with terrain in place of
buildings and one regolith material derived from the LunaCov dielectric. The
Sionna ray-trace is isolated in rt.LunarTwin.load / link_cir (lazy import);
mesh, material, scene XML and CIR->LinkTaps conversion run without Sionna.

Two interchangeable CIR sources -> one emulator:
  LunaCov  (analytic two-ray + Deygout, real-time)  --.
                                                       >-- lchem.to_lchem_pdp -> LCHEM
  LunarTwin (Sionna RT, offline high-fidelity)      --'

Usage
-----
>>> from lunarcomms.twin import LunarTwin
>>> from lunarcomms.export import lchem
>>> tw = LunarTwin(dem, pixel_size_m=5.0)
>>> tw.build("scene_out", stride=2)      # DEM -> mesh + scene (no Sionna)
>>> tw.load(freq_hz=2.5e9)               # needs Sionna RT
>>> lk = tw.link_taps(tx_xyz, rx_xyz, 2.5e9)
>>> pdp = lchem.to_lchem_pdp(lk)         # same MT-012 slot as LunaCov
"""

from .materials import regolith_material_params
from .mesh import dem_to_mesh, write_ply
from .rt import LunarTwin, sionna_cir_to_linktaps, write_mitsuba_scene

__all__ = [
    "LunarTwin",
    "dem_to_mesh",
    "write_ply",
    "regolith_material_params",
    "sionna_cir_to_linktaps",
    "write_mitsuba_scene",
]

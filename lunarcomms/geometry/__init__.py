"""
lunarcomms.geometry
===================
SPICE-based lunar coordinate frames, horizon masking, and Earth visibility.

Modules
-------
frames   : ME↔PA frame rotation; DE421→DE440 transform; Earth-Moon geometry.
horizon  : Raycasting horizon mask from PGDA DEM; line-of-sight grid.
"""

from . import frames, horizon

__all__ = ["frames", "horizon"]

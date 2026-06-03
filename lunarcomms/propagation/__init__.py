"""
lunarcomms.propagation
======================
RF propagation models for the lunar surface environment.

Modules
-------
friis          : Free-space path loss (Friis transmission equation).
two_ray        : Two-ray ground reflection model over flat lunar regolith.
diffraction    : ITU-R P.526-15 multi-edge knife-edge diffraction (Deygout method).

Usage
-----
>>> from lunarcomms.propagation import friis, two_ray, diffraction
>>> pl = two_ray.path_loss_db(5000, h_tx=30, h_rx=2, freq_hz=2.5e9)
"""

from . import diffraction, friis, two_ray

__all__ = ["friis", "two_ray", "diffraction"]

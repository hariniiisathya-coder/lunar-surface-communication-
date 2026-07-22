"""Channel-tap export: pipeline -> emulator/link-level formats.

taps.py : per-link and per-trajectory tap models (delays + complex gains)
          from the two-ray + Deygout physics, with exporters for MATLAB
          nrTDLChannel (DelayProfile='Custom') and Colosseum/MCHEM-style
          4-tap grids.
"""

from . import taps  # noqa: F401

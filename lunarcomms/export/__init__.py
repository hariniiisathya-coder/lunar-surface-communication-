"""Channel-tap export: pipeline -> emulator/link-level formats.

taps.py  : per-link and per-trajectory tap models (delays + complex gains)
           from the two-ray + Deygout physics, with exporters for MATLAB
           nrTDLChannel (DelayProfile='Custom') and Colosseum/MCHEM-style
           4-tap grids.
lchem.py : LCHEM (USRP X410 RFNoC HIL emulator) MT-012 PDP frames --
           complex-16 / real-32 taps, 10 ns ticks, Q1.15 coefficients, and
           the shiftright/RF analog-scale split.
"""

from . import lchem, taps  # noqa: F401

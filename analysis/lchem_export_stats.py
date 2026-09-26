"""Statistics of an LCHEM MT-012 export (paper Table "LCHEM Export"): taps per
link, excess delay, shiftright, and the RF residual attenuation of served and
unserved links. A link is served when its applied attenuation (shiftright x
6.02 dB + RF residual, i.e. the channel loss) is at most EIRP + Grx - sens.
Usage: python analysis/lchem_export_stats.py examples/lchem_<site>_S.json [sens_dBm]
"""
import json
import sys

from lunarcomms.coverage.defaults import EIRP_DBM, GRX_DBI, SENS_DBM

fr = [x[0] if isinstance(x, list) else x for x in json.load(open(sys.argv[1]))]
sens = float(sys.argv[2]) if len(sys.argv) > 2 else SENS_DBM
lim = EIRP_DBM + GRX_DBI - sens
att = [f["shiftright_bits"] * 6.0206 + f["rf_residual_db"] for f in fr]
srv = [f["rf_residual_db"] for f, a in zip(fr, att) if a <= lim]
uns = [f["rf_residual_db"] for f, a in zip(fr, att) if a > lim]
nt = [len(f["coeffs"]) for f in fr]
print(f"links {len(fr)}; taps {min(nt)}-{max(nt)}; one/two taps {nt.count(1)}/{nt.count(2)}; "
      f"max excess delay {max(max(f['delays_10ns']) for f in fr)} ticks; "
      f"shiftright {sorted({f['shiftright_bits'] for f in fr})}")
print(f"sens {sens} dBm (loss limit {lim:.1f} dB): served {len(srv)} residual {min(srv):.1f} to {max(srv):.1f} dB; "
      f"unserved {len(uns)} residual {min(uns):.1f} to {max(uns):.1f} dB")

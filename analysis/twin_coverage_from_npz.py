"""Recompute the LunaCov / LunaTwin served fractions of the 10 km comparison
(analysis/twin_vs_lunacov_10km.py) for another receiver sensitivity, from the
saved per-band maps (served <=> map + offset > 0, offset = EIRP + Grx - sens).
Usage: python analysis/twin_coverage_from_npz.py <twin10km_dir> [sens_dBm]
Writes <dir>/twin10km_sens<sens>.json with the fields of twin10km.json.
"""
import json
import sys

import numpy as np

from lunarcomms.coverage.defaults import EIRP_DBM, GRX_DBI, SENS_DBM

d = sys.argv[1]
sens = float(sys.argv[2]) if len(sys.argv) > 2 else SENS_DBM
off = EIRP_DBM + GRX_DBI - sens
res = {"offset_db": off, "sens_dbm": sens}
for name in ("UHF", "S", "Ka", "S_refraction"):
    D = np.load(f"{d}/twin10km_{name}.npz")
    los = D["los"].astype(bool); shadow = ~los
    st, sl = (D["twin"] + off) > 0, (D["luna"] + off) > 0
    res["los_frac"] = float(los.mean())
    res[name] = {"twin_cov": float(st.mean()), "lunacov_cov": float(sl.mean()),
                 "twin_served_in_shadow": float((st & shadow).sum() / shadow.sum()),
                 "lunacov_served_in_shadow": float((sl & shadow).sum() / shadow.sum()),
                 "los_served_twin": float(st[los].mean()), "los_served_lunacov": float(sl[los].mean()),
                 "no_path_frac": float((D["npaths"] == 0).mean())}
out = f"{d}/twin10km_sens{sens:g}.json"
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1)); print("wrote", out)

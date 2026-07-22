"""
Evidence script: verifies that the Fresnel-Kirchhoff diffraction parameter
(nu) scales with the square root of frequency, as ITU-R P.526-15 predicts,
for a FIXED physical obstacle (a 200 m rim, 2.5 km from Tx and 2.5 km from Rx).

This is a code-correctness / physics-consistency check: since
    nu = h * sqrt(2/lambda * (1/d1 + 1/d2)),  lambda = c/f
the ratio nu(f2)/nu(f1) must equal sqrt(f2/f1) exactly, for ANY fixed
h, d1, d2 -- this follows from algebra alone. Running it confirms the
implementation matches the formula it claims to implement.

Run from the project root:  python nu_frequency_scaling_evidence.py
"""
import numpy as np
from lunarcomms.propagation import diffraction

# Fixed physical obstacle: 200 m rim, midway on a 5 km path
H_RIM = 200.0
D1 = 2500.0
D2 = 2500.0

BANDS = {"UHF": 0.442e9, "S": 2.5e9, "Ka": 27.0e9}


def main():
    print(f"Fixed obstacle: h={H_RIM} m, d1={D1} m, d2={D2} m\n")

    print("Step 1: nu for each band, via the validated fresnel_kirchhoff_parameter()")
    nus = {}
    for name, f in BANDS.items():
        nu = diffraction.fresnel_kirchhoff_parameter(H_RIM, D1, D2, f)
        nus[name] = nu
        print(f"  {name:4s} (f={f/1e9:6.3f} GHz): nu = {nu:.4f}")

    print("\nStep 2: predicted ratio = sqrt(frequency ratio)")
    pred_uhf_s = np.sqrt(BANDS["S"] / BANDS["UHF"])
    pred_s_ka = np.sqrt(BANDS["Ka"] / BANDS["S"])
    print(f"  predicted UHF->S ratio = sqrt({BANDS['S']/1e9:.3f}/{BANDS['UHF']/1e9:.3f}) = {pred_uhf_s:.4f}")
    print(f"  predicted S->Ka  ratio = sqrt({BANDS['Ka']/1e9:.3f}/{BANDS['S']/1e9:.3f}) = {pred_s_ka:.4f}")

    print("\nStep 3: actual ratio from the computed nu values")
    actual_uhf_s = nus["S"] / nus["UHF"]
    actual_s_ka = nus["Ka"] / nus["S"]
    print(f"  actual    UHF->S ratio = {nus['S']:.4f} / {nus['UHF']:.4f} = {actual_uhf_s:.4f}")
    print(f"  actual    S->Ka  ratio = {nus['Ka']:.4f} / {nus['S']:.4f} = {actual_s_ka:.4f}")

    print("\nStep 4: match check")
    print(f"  UHF->S : predicted {pred_uhf_s:.4f} vs actual {actual_uhf_s:.4f}  "
          f"(diff = {abs(pred_uhf_s - actual_uhf_s):.6f})")
    print(f"  S->Ka  : predicted {pred_s_ka:.4f} vs actual {actual_s_ka:.4f}  "
          f"(diff = {abs(pred_s_ka - actual_s_ka):.6f})")


if __name__ == "__main__":
    main()

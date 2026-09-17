"""
Tap-domain figures over a REAL PGDA LOLA DEM (or synthetic fallback):
  B' - along-track two-ray fading on a rover radial from the BTS, with vs
       without surface roughness and antenna downtilt (where the antenna /
       roughness contribution actually shows).
  C' - specular->diffuse transition rho_s(frequency) for cm-scale regolith
       micro-roughness. NOTE: the Rayleigh sigma_h for COHERENT reflection is
       the wavelength-scale (cm) surface texture -- NOT the DEM's terrain
       relief, which the LOS/diffraction geometry already handles and which a
       5 m DEM cannot resolve. So sigma_h here is a literature micro-roughness
       (default 2 cm, LUNAR_SIGMA_H_CM); the DEM's metre-scale relief is only
       reported as context, never fed into rho_s.

Usage:
  LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif \
      python examples/fading_specular_pgda.py
"""
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunarcomms import bands  # noqa: E402
from lunarcomms.export import taps  # noqa: E402
from lunarcomms.propagation import roughness  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEM_PATH = os.environ.get("LUNAR_DEM")
CLIP_KM = float(os.environ.get("LUNAR_CLIP_KM", "6"))
# cm-scale regolith micro-roughness for the specular factor (literature; the
# DEM cannot resolve this). Radar/photometric studies put lunar RMS height at
# ~1-5 cm at cm-dm scales; 2 cm is a reasonable default.
SIGMA_H = float(os.environ.get("LUNAR_SIGMA_H_CM", "2.0")) / 100.0
H_TX, H_RX = 30.0, 2.0


def load_dem():
    if DEM_PATH and os.path.exists(DEM_PATH):
        from lunarcomms.io.pgda import load_dem as _ld
        dem, transform, _ = _ld(DEM_PATH, clip_extent_km=CLIP_KM)
        dem = np.nan_to_num(dem, nan=float(np.nanmin(dem)))
        px = abs(transform[0]) if transform is not None else 5.0
        return dem, px, os.path.basename(DEM_PATH)
    n, px = 400, 5.0
    return np.zeros((21, n)), px, "synthetic-flat"


def terrain_relief_m(dem, px, win_m=100.0):
    """DEM metre-scale relief (detrended RMS at ~win_m) -- CONTEXT ONLY. This
    is terrain, handled by LOS/diffraction; it is NOT the specular sigma_h."""
    from scipy.ndimage import uniform_filter
    w = max(int(win_m / px), 3)
    return float(np.sqrt(np.mean((dem - uniform_filter(dem, w)) ** 2)))


def main():
    dem, px, name = load_dem()
    ny, nx = dem.shape
    sigma_h = SIGMA_H
    relief = terrain_relief_m(dem, px) if "synthetic" not in name else 0.0
    print(f"DEM {name}: shape={dem.shape} px={px:g}m  "
          f"terrain relief ~{relief:.1f} m (context)  "
          f"micro-sigma_h={sigma_h*100:.1f} cm (specular)")

    # ---- B': along-track fading at Ka on a radial from a BTS on a local high.
    tx = np.unravel_index(np.argmax(dem), dem.shape)
    row = int(tx[0])
    cols = list(range(int(tx[1]) + 3, min(nx, int(tx[1]) + 3 + 360)))
    path = [(row, c) for c in cols]
    d = np.array([(c - tx[1]) * px for c in cols])
    F = bands.freq_hz("Ka")

    def trace(**kw):
        lks = taps.trajectory_taps(dem, px, row, int(tx[1]), path,
                                   H_TX, H_RX, F, **kw)
        out = []
        for lk in lks:
            g = lk.collapsed().gains
            out.append(20 * np.log10(max(abs(np.sum(g)), 1e-9)) if lk.los else np.nan)
        return np.array(out)

    from lunarcomms.antenna import ThreeGPP38901Element as El
    figb, axb = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    axb.plot(d / 1e3, trace(), lw=0.8, label="smooth, isotropic")
    axb.plot(d / 1e3, trace(sigma_h_m=sigma_h), lw=1.1,
             label=f"rough sigma_h={sigma_h*100:.1f} cm (regolith micro)")
    axb.plot(d / 1e3, trace(tx_pattern=El(hpbw_el_deg=20, downtilt_deg=10)),
             lw=0.8, alpha=0.8, label="narrow mast, 10 deg downtilt")
    axb.set_xlabel("along-track distance from BTS (km)")
    axb.set_ylabel("collapsed tap gain rel. direct ray (dB)")
    axb.set_title(f"Ka along-track two-ray fading over real terrain ({name})")
    axb.legend()
    axb.grid(alpha=0.3)
    figb.savefig(f"{HERE}/fadingBp_{os.path.splitext(name)[0]}.png", dpi=120)
    plt.close(figb)

    # ---- C': specular->diffuse transition, sigma_h anchored to this DEM.
    freqs = np.logspace(np.log10(0.3e9), np.log10(200e9), 400)
    theta = np.deg2rad(5.0)
    figc, axc = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for s_cm in sorted({round(sigma_h * 100, 1), 0.5, 1.0, 5.0}):
        rho_s = roughness.specular_factor(s_cm / 100.0, freqs, theta)
        is_def = abs(s_cm - sigma_h * 100) < 0.05
        lab = f"sigma_h={s_cm:g} cm" + (" (default)" if is_def else "")
        axc.semilogx(freqs / 1e9, rho_s, label=lab)
    for b in ("UHF", "S", "Ka", "D"):
        axc.axvline(bands.freq_hz(b) / 1e9, color="k", ls=":", alpha=0.4)
        axc.text(bands.freq_hz(b) / 1e9, 1.02, b, ha="center", fontsize=8)
    axc.set_xlabel("frequency (GHz)")
    axc.set_ylabel(r"coherent reflection factor $\rho_s$")
    axc.set_title(f"Specular -> diffuse transition (grazing 5 deg; {name})")
    axc.legend()
    axc.grid(alpha=0.3, which="both")
    axc.set_ylim(0, 1.05)
    figc.savefig(f"{HERE}/specularCp_{os.path.splitext(name)[0]}.png", dpi=120)
    plt.close(figc)

    los_frac = np.mean(np.isfinite(trace()))
    rs_ka = roughness.specular_factor(sigma_h, bands.freq_hz("Ka"), theta)
    print(f"radial LOS fraction {los_frac:.0%}; "
          f"Ka rho_s at 5deg (sigma_h={sigma_h*100:.0f}cm) = {rs_ka:.3f}")
    print(f"wrote fadingBp_/specularCp_ for {name}")


if __name__ == "__main__":
    main()

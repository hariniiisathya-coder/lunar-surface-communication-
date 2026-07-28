"""
Variable-regolith two-ray vs uniform baseline, using the Siegler et al. (2020)
spatial loss-tangent maps sampled at the DEM site's true lat/lon.

Pipeline (the original Paper-2 plan, stage 1):
  DEM (polar stereographic) -> site lat/lon (pyproj) -> Siegler a',b'
  -> tan_delta = 10^(a' + f^b') -> Fresnel Gamma -> two-ray path loss,
  compared against the uniform-regolith baseline.

Data:
  Siegler a'/b' maps: Zenodo 10.5281/zenodo.3993798 (JGR Planets 2020,
  doi:10.1029/2020JE006405). Place the two .txt rasters and set:
    LUNAR_SIEGLER_A=data/siegler/a_prime.txt
    LUNAR_SIEGLER_B=data/siegler/b_prime.txt
    LUNAR_DEM=data/dem/Site01_final_adj_5mpp_surf.tif
"""
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunarcomms import bands  # noqa: E402
from lunarcomms.propagation import two_ray  # noqa: E402
from lunarcomms.regolith import dielectric  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEM = os.environ.get("LUNAR_DEM", "data/dem/Site01_final_adj_5mpp_surf.tif")
A = os.environ.get("LUNAR_SIEGLER_A", "data/siegler/a_prime.txt")
B = os.environ.get("LUNAR_SIEGLER_B", "data/siegler/b_prime.txt")
H_TX, H_RX = 30.0, 2.0


def site_latlon(dem_path):
    import rasterio
    from pyproj import Transformer
    with rasterio.open(dem_path) as s:
        cx, cy = s.transform * (s.width / 2, s.height / 2)
        tr = Transformer.from_crs(s.crs, s.crs.geodetic_crs, always_xy=True)
    lon, lat = tr.transform(cx, cy)
    return lat, lon % 360.0


def main():
    from lunarcomms.io.pgda import sample_loss_tangent_params
    lat, lon = site_latlon(DEM)
    ap, bp = sample_loss_tangent_params(lat, lon, A, B)
    ap, bp = float(ap), float(bp)
    name = os.path.basename(DEM)
    print(f"{name}: lat={lat:.2f} lon={lon:.1f}  Siegler a'={ap:.3f} b'={bp:.3f}")

    print("  tan_delta (uniform rho=1.5 vs Siegler-spatial):")
    for nm in ("UHF", "S", "Ka"):
        f = bands.freq_hz(nm) / 1e9
        td_u = dielectric.loss_tangent(1.5, f)
        td_s = float(dielectric.loss_tangent_ab(ap, bp, f))
        print(f"    {nm:>3} {f:6.2f} GHz : uniform={td_u:.5f}  spatial={td_s:.5f}"
              f"  ({td_s/td_u:.2f}x)")

    # Where it bites: short range (steep grazing), S-band.
    d = np.linspace(40, 3000, 400)
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for nm, c in (("UHF", "tab:blue"), ("S", "tab:orange")):
        f = bands.freq_hz(nm)
        pl_u = two_ray.path_loss_db(d, H_TX, H_RX, f)
        pl_s = two_ray.path_loss_spatial_db(d, H_TX, H_RX, f, ap, bp)
        ax.plot(d, pl_s - pl_u, color=c, label=f"{nm} (spatial - uniform)")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("distance (m)")
    ax.set_ylabel("two-ray PL difference (dB)")
    ax.set_title(f"Variable regolith vs uniform ({name}, a'={ap:.2f} b'={bp:.2f})")
    ax.legend()
    ax.grid(alpha=0.3)
    out = os.path.join(HERE, f"regolith_{os.path.splitext(name)[0]}.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

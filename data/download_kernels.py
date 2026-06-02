"""
Download NAIF SPICE kernels required for Earth-Moon geometry calculations.

Kernels downloaded
------------------
    naif0012.tls        Leap-second kernel (LSK)
    de440.bsp           JPL planetary ephemeris (SPK) — includes Moon
    pck00011.tpc        Planetary constants kernel (radii, GM values)
    moon_pa_de440_200625.bpc  Lunar body-fixed orientation (binary PCK)

Source: https://naif.jpl.nasa.gov/pub/naif/generic_kernels/

Usage
-----
    python data/download_kernels.py              # download all to data/kernels/
    python data/download_kernels.py --outdir /custom/path

After downloading, load in Python with spiceypy:
    import spiceypy as spice
    spice.furnsh("data/kernels/naif0012.tls")
    spice.furnsh("data/kernels/de440.bsp")
    spice.furnsh("data/kernels/pck00011.tpc")
    spice.furnsh("data/kernels/moon_pa_de440_200625.bpc")
"""

import argparse
import urllib.request
from pathlib import Path

NAIF_BASE = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"

KERNELS = [
    (f"{NAIF_BASE}/lsk/naif0012.tls",
     "naif0012.tls",
     "Leap-second kernel (required by all SPICE calls)"),
    (f"{NAIF_BASE}/spk/planets/de440.bsp",
     "de440.bsp",
     "JPL DE440 planetary ephemeris — Earth, Moon, Sun (~113 MB)"),
    (f"{NAIF_BASE}/pck/pck00011.tpc",
     "pck00011.tpc",
     "Planetary constants — lunar radii, GM, orientation parameters"),
    (f"{NAIF_BASE}/pck/moon_pa_de440_200625.bpc",
     "moon_pa_de440_200625.bpc",
     "Lunar body-fixed orientation binary PCK (~8 MB)"),
]


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  already exists: {dest.name}")
        return

    def _hook(count, block, total):
        if total > 0:
            pct = min(count * block * 100 // total, 100)
            print(f"\r  {dest.name}: {pct}%", end="", flush=True)

    print(f"  downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest, reporthook=_hook)
    print()


def main():
    parser = argparse.ArgumentParser(description="Download NAIF SPICE kernels")
    parser.add_argument("--outdir", default="data/kernels",
                        help="Output directory (default: data/kernels)")
    parser.add_argument("--list", action="store_true",
                        help="List kernels that would be downloaded")
    args = parser.parse_args()

    print("NAIF SPICE kernels for Earth-Moon geometry")
    print(f"Output: {args.outdir}/\n")

    for url, filename, description in KERNELS:
        if args.list:
            print(f"  {filename:45s}  {description}")
            continue
        dest = Path(args.outdir) / filename
        print(f"{description}")
        download_file(url, dest)
        print(f"  -> {dest}\n")

    if not args.list:
        metakernel = Path(args.outdir) / "meta.tm"
        lines = [
            "\\begindata",
            "KERNELS_TO_LOAD = (",
        ]
        for _, filename, _ in KERNELS:
            lines.append(f"    '{Path(args.outdir) / filename}'")
        lines += [")", "\\begintext"]
        metakernel.write_text("\n".join(lines) + "\n")
        print(f"Meta-kernel written: {metakernel}")
        print("Load with: spice.furnsh('data/kernels/meta.tm')")


if __name__ == "__main__":
    main()

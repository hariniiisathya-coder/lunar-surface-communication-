"""
Download PGDA-78 high-resolution LOLA DEMs for lunar south pole landing sites.

Source: https://pgda.gsfc.nasa.gov/products/78
Reference: Barker et al. (2021), Planetary & Space Science 203, 105119.
           doi:10.1016/j.pss.2020.105119

Usage
-----
    python data/download_pgda.py              # downloads Site01 (Connecting Ridge)
    python data/download_pgda.py --site Site04  # Shackleton rim
    python data/download_pgda.py --list        # show all available sites

Available sites (PGDA-78)
-------------------------
    Site01  Connecting Ridge       <- scenario BTS location
    Site04  Shackleton rim
    Site06  Nobile rim 1
    Site07  Peak near Shackleton
    Site11  de Gerlache rim
    Site20  Leibnitz beta plateau
    Site23  Malapert massif
    Haworth Haworth crater
    Shoemaker Shoemaker crater
    DM2     Nobile rim 2
"""

import argparse
import hashlib
import urllib.request
from pathlib import Path

BASE_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp"

SITES = {
    "Site01": "Connecting Ridge (scenario BTS location)",
    "Site04": "Shackleton rim",
    "Site06": "Nobile rim 1",
    "Site07": "Peak near Shackleton",
    "Site11": "de Gerlache rim",
    "Site20": "Leibnitz beta plateau",
    "Site23": "Malapert massif",
    "Haworth": "Haworth crater",
    "Shoemaker": "Shoemaker crater",
    "DM2": "Nobile rim 2",
}

PRODUCTS = {
    "surf": "{site}_final_adj_5mpp_surf.tif",
    "slope": "{site}_final_adj_5mpp_slp.tif",
    "error": "{site}_final_adj_5mpp_toterr.tif",
}


def download_file(url: str, dest: Path, show_progress: bool = True) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  already exists: {dest.name}")
        return

    def _hook(count, block, total):
        if show_progress and total > 0:
            pct = min(count * block * 100 // total, 100)
            print(f"\r  {dest.name}: {pct}%", end="", flush=True)

    print(f"  downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest, reporthook=_hook)
    print()


def main():
    parser = argparse.ArgumentParser(description="Download PGDA-78 LOLA DEMs")
    parser.add_argument("--site", default="Site01",
                        help="Site name (default: Site01 = Connecting Ridge)")
    parser.add_argument("--product", default="surf",
                        choices=list(PRODUCTS.keys()),
                        help="Which product to download (default: surf)")
    parser.add_argument("--outdir", default="data/dem",
                        help="Output directory (default: data/dem)")
    parser.add_argument("--list", action="store_true",
                        help="List all available sites and exit")
    args = parser.parse_args()

    if args.list:
        print("Available PGDA-78 sites:")
        for site, desc in SITES.items():
            print(f"  {site:12s}  {desc}")
        return

    if args.site not in SITES:
        raise ValueError(f"Unknown site '{args.site}'. Use --list to see options.")

    filename = PRODUCTS[args.product].format(site=args.site)
    url = f"{BASE_URL}/{args.site}/{filename}"
    dest = Path(args.outdir) / args.site / filename

    print(f"Site:    {args.site} — {SITES[args.site]}")
    print(f"Product: {args.product} ({filename})")
    print(f"Source:  {url}")
    download_file(url, dest)
    print(f"Saved:   {dest}")


if __name__ == "__main__":
    main()

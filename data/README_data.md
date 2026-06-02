# Data Downloads

Large data files are NOT committed to this repository. Download them with the
scripts below before running notebooks or tests that require them.

---

## SPICE Kernels (~150 MB total)

Required by: `lunarcomms.geometry.frames`, all SPICE-dependent tests.

```bash
python data/download_kernels.py
```

Downloads to `data/kernels/`:

| File | Size | Source | Purpose |
|------|------|--------|---------|
| `de440.bsp` | ~120 MB | [NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/) | Planetary + lunar ephemerides |
| `moon_pa_de440_200625.bpc` | ~2 MB | [NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/) | Moon orientation (PA frame) |
| `moon_de440_220930.tf` | ~10 KB | [NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/) | ME↔PA frame definition |
| `latest_leapseconds.tls` | ~5 KB | [NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/) | Leap seconds |

NAIF SPICE toolkit: https://naif.jpl.nasa.gov/naif/toolkit.html

---

## PGDA South Pole DEM (~2 GB)

Required by: `lunarcomms.io.pgda`, coverage map notebooks.

```bash
python data/download_pgda.py --product 78
```

Downloads to `data/dems/`:

| Product | Resolution | Size | URL |
|---------|-----------|------|-----|
| PGDA-78 (DEM 5 m) | 5 m/px | ~2 GB | https://pgda.gsfc.nasa.gov/products/78 |
| PGDA-81 (illumination) | 240 m/px | ~50 MB | https://pgda.gsfc.nasa.gov/products/81 |
| PGDA-98 (roughness) | 5 m/px | ~500 MB | https://pgda.gsfc.nasa.gov/products/98 |

For development without the full 2 GB DEM, use a 40-km clip:
```bash
python data/download_pgda.py --product 78 --clip 40  # ~30 MB
```

**Projection:** Polar Stereographic (south), EPSG:104903 (lunar ME)
**Datum:** MOON_ME, DE440
**Vertical datum:** Mean lunar radius 1737.4 km
**Reference:** Barker et al. (2016), doi:10.1016/j.icarus.2016.02.008

---

## Siegler 2020 Regolith Density Map (~10 MB)

Required by: `lunarcomms.io.pgda.sample_density()` (Track S1 Week 5).

```bash
python data/download_pgda.py --siegler2020
```

Downloads `lunar_density_map.tif` from Zenodo:
https://zenodo.org/record/3834965

**Resolution:** ~8 km/px (LRO Diviner footprint)
**Coverage:** Global
**Reference:** Siegler et al. (2020), doi:10.1029/2020JE006405

---

## LCRNS Reference Constellation 3.1 (included)

**Already in this repo:** `data/orbits/lcrns_ref_constellation.json`

Orbital elements extracted from:
Guinn et al. (2025), NTRS 20250002698.
https://ntrs.nasa.gov/citations/20250002698

No download needed.

---

## Mini-RF CPR (optional, for validation)

Used for regolith scattering validation (Track S1 stretch goal).

Download from NASA PDS Geosciences Node:
https://pds-geosciences.wustl.edu/missions/lro/minirf.htm

Select: Mini-RF Level 2 (CPR) data, south pole tiles, S-band.
Reference: Cahill et al. (2014), doi:10.1016/j.icarus.2014.08.025

---

## Total storage budget

| Dataset | Size | Required for |
|---------|------|-------------|
| SPICE kernels | ~150 MB | S1, S2, S3 (geometry) |
| PGDA-78 full | ~2 GB | S1 (full coverage maps) |
| PGDA-78 clip 40km | ~30 MB | S1 (development) |
| PGDA-81 illumination | ~50 MB | S1 (optional validation) |
| PGDA-98 roughness | ~500 MB | S1 (stretch goal) |
| Siegler 2020 density | ~10 MB | S1 Week 5+ |
| LCRNS elements (JSON) | <1 KB | S2, S3 (included) |

**Minimum to get started:** SPICE kernels + PGDA-78 clip (~180 MB)

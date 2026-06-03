# lunar-comms-survey

**A living survey and open-source toolchain for lunar wireless communications.**

[![CI](https://github.com/ebaenamar/lunar-comms-survey/actions/workflows/ci.yml/badge.svg)](https://github.com/ebaenamar/lunar-comms-survey/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## What this is

This repository pairs a **structured technical survey** of lunar communications methodology with a **minimal, reproducible Python toolchain** that closes the most accessible gaps. It is designed to be useful to:

- Students beginning research in lunar wireless communications.
- Researchers who need validated open-source implementations of lunar propagation models.
- Mission engineers who want reproducible link budgets and coverage maps for south-pole lunar scenarios.

The survey identifies, for each topic area, what the published literature actually measures, what it silently assumes, and where the open-source tooling is missing. Every gap maps to a module in this package.

---

## Background: why this exists

NASA Artemis, LCRNS (Lunar Communications Relay and Navigation Services), ESA Moonlight/Lunar Pathfinder, and CNSA Queqiao-2 are building the first permanent lunar communications infrastructure. Future operations at the lunar south pole will require RF links among astronauts, rovers, habitats, landers, relays in elliptical lunar frozen orbits (ELFO), and Earth ground stations.

Despite growing interest, **no public open-source toolchain** integrates:
- Realistic lunar terrain (LOLA/PGDA 5 m DEMs) with validated regolith dielectric models.
- Correct ELFO relay geometry from public ephemerides.
- Surface propagation physics beyond a generic Friis equation.

This repository builds that toolchain incrementally, documented by the survey.

---

## The three research tracks

This repo supports three parallel summer internship tracks. All three share the same scenario: a lander/BTS at **Connecting Ridge** (lunar south pole), a relay in **LCRNS/Moonlight ELFO** (~17 400 km apoapsis, ~30 h period), and Earth ~1.28 light-seconds away.

```
  ┌─────────┐
  │   DSN   │  Earth (1.28 s one-way)
  └────┬────┘
       │ X-band trunk
  ┌────┴─────────┐
  │ LCRNS / Lunar│  ELFO: ~30 h period, apoapsis over south pole
  │ Pathfinder   │  ~15–20 h visible per orbit from surface
  └────┬─────────┘
       │ S-band 2.5 GHz (SFCGb1 / LunaNet AFS 2492 MHz)
  ┌────┴────┐
  │ Lander  │  Connecting Ridge  (~89.5°S, elevation ~3 200 m)
  │  / BTS  │  BTS antenna height 10–30 m
  └────┬────┘
       │ 5G NR surface  (S-band / UHF)
  ┌────┴────┐
  │Rover/EVA│  ~1–10 km radius, antenna 2 m height
  └─────────┘
```

| Track | Owner | Key modules | Survey chapters |
|-------|-------|-------------|----------------|
| **S1** Surface RF propagation + coverage maps | Student 1 | `regolith`, `propagation`, `coverage`, `io` | 03, 04 |
| **S2** 3GPP/5G stack adaptation for the Moon | Student 2 | `orbits`, `geometry`, `propagation` | 02, 05 |
| **S3** DTN / Solar System Internet | Student 3 | `orbits`, `geometry` (contact plans) | 02, 06 |

---

## Repository structure

```
lunar-comms-survey/
├── README.md                        # this file
├── TASKS.md                         # student task assignments and open issues
├── CITATION.cff                     # how to cite this repo
├── pyproject.toml                   # single dependency list
├── environment.yml                  # conda alternative
├── LICENSE
│
├── lunarcomms/                      # installable Python package
│   ├── geometry/                    # SPICE kernels, frames, horizon masking
│   │   ├── frames.py                # ME↔PA frame rotation, DE421↔DE440
│   │   └── horizon.py               # raycasting horizon mask from DEM
│   ├── orbits/                      # relay orbit propagation and contact plans
│   │   ├── elfo.py                  # ELFO Keplerian propagation, Folta-Quinn design
│   │   └── lcrns.py                 # LCRNS Reference Constellation 3.1 loader
│   ├── regolith/                    # dielectric models (FIRST MODULE — start here)
│   │   └── dielectric.py            # Olhoeft+Strangway 1975, Siegler 2020
│   ├── propagation/                 # RF propagation models
│   │   ├── friis.py                 # free-space path loss
│   │   ├── two_ray.py               # two-ray ground reflection over regolith
│   │   └── diffraction.py           # ITU-R P.526-15 multi-edge Deygout
│   ├── coverage/                    # link margin → GeoTIFF
│   │   └── link_budget.py
│   └── io/                          # data readers
│       └── pgda.py                  # PGDA GeoTIFF reader (polar stereographic)
│
├── tests/
│   ├── test_regolith.py             # validated against Olhoeft 1975 Table 2
│   ├── test_propagation.py          # free-space limit + breakpoint check
│   └── test_geometry.py             # SPICE Earth-Moon distance vs Horizons
│
├── docs/
│   ├── survey/                      # the living survey (one .md per chapter)
│   │   ├── 00-scope.md
│   │   ├── 01-geometry-and-frames.md
│   │   ├── 02-relay-architectures.md
│   │   ├── 03-rf-propagation.md
│   │   ├── 04-regolith-dielectrics.md
│   │   ├── 05-3gpp-on-the-moon.md
│   │   ├── 06-dtn-and-solar-system-internet.md
│   │   ├── 07-tooling-and-gaps.md
│   │   ├── 08-open-problems.md
│   │   └── references.bib           # BibTeX — add entries here
│   └── tutorials/                   # worked Jupyter notebooks
│
├── notebooks/
│   ├── 01-load-spice-and-de440.ipynb
│   ├── 02-open-pgda-dem.ipynb
│   ├── 03-propagate-lcrns-elfo.ipynb
│   ├── 04-horizon-mask-from-dem.ipynb
│   ├── 05-regolith-dielectric-map.ipynb
│   ├── 06-two-ray-and-fresnel.ipynb
│   └── 07-first-link-budget.ipynb
│
├── data/
│   ├── README_data.md               # how to download all datasets
│   ├── kernels/                     # SPICE kernels (NOT committed — see download script)
│   ├── dems/                        # PGDA DEM tile manifests (JSON only)
│   └── orbits/                      # LCRNS 3.1 reference states (JSON)
│
└── .github/
    └── workflows/
        └── ci.yml                   # run pytest on every push
```

---

## Quick start

### Install

```bash
git clone https://github.com/ebaenamar/lunar-comms-survey.git
cd lunar-comms-survey
pip install -e ".[dev]"
```

Or with conda:

```bash
conda env create -f environment.yml
conda activate lunarcomms
pip install -e ".[dev]"
```

### Download data

```bash
python data/download_kernels.py      # SPICE DE440 + lunar PCK (~150 MB)
python data/download_pgda.py         # PGDA-78 south pole DEM 5 m (~2 GB tile)
```

### Run tests

```bash
pytest tests/ -v
```

### First result (< 5 min from install)

```python
from lunarcomms.regolith import dielectric

# Bulk density of lunar regolith surface layer (Carrier et al. 1991)
rho = 1.50  # g/cm^3

# Dielectric properties at S-band
eps_r   = dielectric.permittivity(rho)        # → 2.69
tan_d   = dielectric.loss_tangent(rho, 2.5)   # → 0.0082 at 2.5 GHz

print(f"ε' = {eps_r:.3f},  tan δ = {tan_d:.4f}")
```

---

## Survey structure

Each chapter in `docs/survey/` follows a fixed five-part template:

1. **What the literature does** — models used, datasets, key papers.
2. **Silent assumptions** — what is extrapolated or assumed without measurement support.
3. **Measurement support vs. extrapolation** — explicit audit of credibility.
4. **The gap** — named in one sentence.
5. **This repo's response** — link to the module that addresses it, or `TODO` if open.

This structure makes the survey a specification for the codebase, not just a bibliography.

---

## Adding references

All references live in `docs/survey/references.bib`. Add BibTeX entries there and cite them in survey chapters as `[@key]`. Run `make survey` (coming soon) to render the full survey to PDF via Pandoc + pandoc-citeproc.

The format for an entry is standard BibTeX:

```bibtex
@article{olhoeft1975,
  author  = {Olhoeft, G. R. and Strangway, D. W.},
  title   = {Dielectric properties of the first 100 meters of the Moon},
  journal = {Earth and Planetary Science Letters},
  year    = {1975},
  volume  = {24},
  pages   = {394--408},
  doi     = {10.1016/0012-821X(75)90146-6}
}
```

---

## Contributing

This is a summer internship repository. Each student owns their track and is responsible for:

- Implementing the modules in their track (see `TASKS.md`).
- Writing/extending the survey chapters corresponding to their track.
- Adding any new references to `references.bib`.
- Keeping tests green on every push.

See `TASKS.md` for the full task breakdown and open items.

---

## License

MIT License. See `LICENSE`.

---

## Citation

If you use this repository in your work, please cite it using the metadata in `CITATION.cff`.

---

## Key references

A subset of the most important references for this project. Full list in `docs/survey/references.bib`.

| Reference | What it provides |
|-----------|-----------------|
| Olhoeft & Strangway (1975) | Canonical regolith permittivity formula ε' = 1.919^ρ |
| Siegler et al. (2020) | Global regolith loss tangent map |
| Mazarico et al. (2011) | South pole illumination model (Shackleton, PSRs) |
| Folta & Quinn (2006) | ELFO design — canonical reference for relay orbits |
| Edwards et al. (2023) | 3GPP/5G on the Moon — system-level analysis |
| 3GPP TR 38.811 | NTN channel model |
| 3GPP TR 38.821 | NTN system study |
| LunaNet ICD v5 | LunaNet Interoperability Specification |
| SFCG REC 32-2R6 | Lunar frequency coordination |
| CCSDS 734.2-B-2 | Bundle Protocol v7 specification |
| LCRNS Ref. Const. 3.1 (NTRS 20250002698) | LCRNS ephemerides and orbit parameters |
| Toonen et al. (2022) | Lunar surface-to-surface coverage baseline |

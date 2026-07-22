# lunar-comms-survey — S1 Surface RF Propagation & Coverage

A validated, open-source Python pipeline for predicting radio coverage on
the lunar surface, combining LOLA/PGDA-78 terrain diffraction with
spatially-variable regolith dielectrics. Built as the Student-1 (S1) track
of a summer research project on lunar wireless communications.

## What this is

Given a transmitter location on a real lunar DEM (LOLA/PGDA-78, 5 m/pixel),
this pipeline predicts, for every point in the surrounding terrain, whether
a receiver would have a working radio link — accounting for:

- **Free-space and two-ray propagation**, including a real Fresnel
  reflection coefficient derived from regolith permittivity.
- **Spatially-variable regolith dielectric loss**, from validated global
  loss-tangent maps.
- **Terrain diffraction** over crater rims and ridges (ITU-R P.526-15
  Deygout multi-edge method), using real line-of-sight raycasting over the
  DEM.

The headline finding: **on real terrain at the lunar south pole, coverage
is set by terrain blockage, not by path loss.** A flat-ground, free-space
model predicts ~100% coverage over a 2 km test area at Connecting Ridge;
the terrain-aware model predicts 68.5% — the missing 31.5% is signal lost
to line-of-sight shadowing behind ridges and crater rims. Published lunar
link-budget studies that assume flat ground (e.g. Edwards et al., 2023) miss
this entirely; terrain-aware radio maps do exist (RADIOLUNADIFF's Sionna
ray-tracing over LOLA, 2025; Toonen et al. 2022's L99% fade maps), but to
our knowledge no *open-source* coverage pipeline combines DEM diffraction
with spatially-variable regolith dielectrics and exports the resulting
channel for 5G link-level simulation.

## Pipeline overview

![Coverage pipeline flowchart](diagrams/coverage_pipeline_detailed.svg)

Each pixel's line-of-sight status determines which physics model applies:
visible pixels use two-ray propagation with a real Fresnel reflection
coefficient sampled from the Siegler regolith map; shadowed pixels use
free-space loss plus Deygout diffraction over the extracted terrain profile.
Both paths merge into a per-pixel link margin.

![Line-of-sight raycasting cross-section](diagrams/los_raycast_cross_section.svg)

The line-of-sight check itself: for every pixel, the terrain elevation
profile between the transmitter and that pixel is compared against the
straight sight line joining their antenna heights. If the terrain rises
above that line anywhere along the path, the pixel is shadowed.

## Key findings

- **Terrain dominates coverage.** Four-level fidelity comparison (Friis →
  two-ray → +Deygout diffraction → +spatial dielectric) isolates each
  physical effect: multipath ≈0% change, terrain diffraction −31.5%,
  spatial dielectric ≈0% at the nominal link budget.
- **The terrain-blockage penalty grows with frequency, as predicted.**
  Tested across UHF (0.442 GHz), S-band (2.5 GHz), and Ka-band (27 GHz) on
  the same real terrain: penalty rises 5.1% → 31.5% → 47.4%, consistent
  with the Fresnel-Kirchhoff diffraction parameter's ν ∝ √f scaling
  (verified to zero numerical difference against theory).
- **Dielectric variation is real but link-budget-conditional.** Regolith
  permittivity produces a genuine, angle-dependent margin effect (up to
  3 dB), but it only changes binary coverage under a stressed link budget —
  under the generous Edwards (2023) parameters, every line-of-sight pixel
  sits 50–90 dB above threshold, so a few dB of dielectric sensitivity
  never flips a pixel's covered/uncovered status.
- **A pre-registered prediction was tested and rejected.** It was predicted
  that dielectric sensitivity would be small at S-band and larger at
  Ka-band (reasoning from diffraction's frequency scaling). Measured
  result: the opposite — S-band's effect (3.44% max coverage change) is
  over 4× larger than Ka-band's (0.80%), because the Fresnel reflection
  coefficient's dependence on real permittivity has no meaningful frequency
  term, unlike diffraction. This comparison was independently re-verified
  at 10× finer EIRP resolution after an initial coarse sweep was found to
  understate both bands' true sensitivity unevenly.

## Channel export: taps for nrTDLChannel and Colosseum

`lunarcomms/export/taps.py` turns the pipeline's physics into tap-delay-line
channels a 5G link-level simulator or hardware emulator can replay:

- **Per-link taps** (`link_taps`): LOS pixels yield the direct ray plus the
  ground reflection (complex gain Γ·(r1/r2)·e^{-jkΔ}, excess delay Δ/c);
  NLOS pixels yield a single Deygout-diffracted tap (−J dB, dominant-edge
  geometric excess delay). Gains are relative to the free-space direct ray;
  `fspl_direct_db` carries the absolute scale.
- **The lunar channel is sparse — and that is a result.** At surface
  geometries (30 m/2 m masts, km-scale links) the two-ray excess delay is
  sub-nanosecond, below any emulator's tap resolution, so both rays collapse
  into one complex tap whose magnitude carries the interference nulls
  (`LinkTaps.collapsed`). 1–3 taps per link: Colosseum/MCHEM's 4-tap,
  10 ns, 5.11 µs grid fits the lunar surface channel with room to spare —
  unlike terrestrial multipath.
- **Trajectory traces** (`trajectory_taps`): tap sets along a rover path —
  the spatial two-ray nulls become the time-fading a moving UE experiences
  (this is also why coverage maps can show moiré near the Tx: the null
  spacing drops below the 5 m DEM pixel and aliases; the physics is real,
  the map sampling is not).
- **Exports:** `save_nrtdl_mat` (MATLAB `nrTDLChannel`,
  `DelayProfile='Custom'`: `PathDelays`/`AveragePathGains`),
  `to_colosseum_taps` (MCHEM grid), `save_json`.
- Locked by `tests/test_taps.py`, including the consistency check that the
  collapsed LOS tap reproduces `two_ray.path_loss_db` to <0.05 dB.

## Install

```bash
pip install -e ".[dev]"
```

or with conda:

```bash
conda env create -f environment.yml && conda activate lunarcomms
```
## Data setup

DEMs for Site01 and Site04 are included in `data/dem/`. The SPICE ephemeris
kernel (`de440.bsp`, ~114 MB) is not tracked in git (exceeds GitHub's file
size limit) — download it from NAIF:
The Siegler (2020) loss-tangent maps are Zenodo record
[10.5281/zenodo.3993798](https://doi.org/10.5281/zenodo.3993798) — place
`Figure 11_Constant Loss Parameter_a'.txt` and
`Figure 11_Frequency Exponent_b'.txt` in the project root.

## Run tests
42 tests in `test_regolith.py` + `test_propagation.py` pass, every expected
value anchored to a named primary source (not to hand-computed or assumed
values). `test_geometry.py`'s line-of-sight tests are this track's own; its
Earth-Moon distance tests are shared common-ground utilities.

## First result

```python
from lunarcomms.regolith import dielectric

rho = 1.50  # g/cm^3 (Carrier et al. 1991)

eps_r = dielectric.permittivity(rho)              # -> 2.658
tan_d = dielectric.loss_tangent(rho, 2.5)         # -> 0.0055 at 2.5 GHz (uniform baseline,
                                                  #    full Siegler 2020 form incl. 0.312*rho)

print(f"eps' = {eps_r:.3f},  tan d = {tan_d:.4f}")
```

For the spatially-variable loss tangent (the validated Siegler form used
throughout the coverage pipeline):

```python
from lunarcomms.io.pgda import sample_loss_tangent_params
from lunarcomms.regolith.dielectric import loss_tangent_ab

a, b = sample_loss_tangent_params(lat=-89.4, lon=222.0,
                                   a_path="Figure 11_Constant Loss Parameter_a'.txt",
                                   b_path="Figure 11_Frequency Exponent_b'.txt")
tan_d = loss_tangent_ab(a, b, freq_ghz=2.5)
```

## Run the analysis scripts

All scripts in `analysis/` must be run **from the project root** (they
reference `data/` and the Siegler `.txt` files with root-relative paths):
## References

| Reference | What it provides | Link |
|---|---|---|
| Olhoeft & Strangway (1975), EPSL 24, 394–408 | Real permittivity ε′ = 1.919^ρ | [doi:10.1016/0012-821X(75)90146-6](https://doi.org/10.1016/0012-821X(75)90146-6) |
| Siegler et al. (2020), JGR Planets 125, e2020JE006405 | Global regolith loss-tangent maps, Figure 8, Table 1 | [doi:10.1029/2020JE006405](https://doi.org/10.1029/2020JE006405) |
| Siegler et al. (2020) — Zenodo dataset | a′/b′ loss-tangent fit coefficient maps | [doi:10.5281/zenodo.3993798](https://doi.org/10.5281/zenodo.3993798) |
| Rappaport (1996), *Wireless Communications: Principles and Practice*, Prentice Hall, ch. 3 | Two-ray ground reflection model, breakpoint distance | ISBN 0-13-375536-3 |
| ITU-R Recommendation P.526-15 (2019) | Knife-edge and Deygout multi-edge diffraction | [itu.int/rec/R-REC-P.526](https://www.itu.int/rec/R-REC-P.526/en) |
| Mazarico et al. (2011), Icarus 211, 1066–1081 | South-pole horizon/illumination raycasting method | [doi:10.1016/j.icarus.2010.10.030](https://doi.org/10.1016/j.icarus.2010.10.030) |
| Edwards et al. (2023), NASA NTRS 20220015268 | South-pole link-budget parameters; Friis-only coverage baseline | [ntrs.nasa.gov/citations/20220015268](https://ntrs.nasa.gov/citations/20220015268) |
| Balanis (2012), *Advanced Engineering Electromagnetics*, Wiley | Fresnel reflection coefficient, coherent two-ray interference theory | ISBN 978-0470589489 |
| Adebowale & Ostermann (2026), *Telecom* 7(1), 21 | Site-specific lunar 5G path-loss exponents (2.54–4.33, Shoemaker Rim F, ray-tracing), the benchmark for this project's planned PLE validation | [doi:10.3390/telecom7010021](https://doi.org/10.3390/telecom7010021) |

**Not yet implemented — references for a planned extension** (a stratified-regolith, multi-layer FIR channel model with subsurface dielectric interfaces, discussed as future work but not part of the current codebase):

| Reference | What it provides | Link |
|---|---|---|
| Wait (1962), *Electromagnetic Waves in Stratified Media*, Pergamon Press | Recursive impedance method for multilayer reflection coefficients | [archive.org/details/electromagneticw0000wait](https://archive.org/details/electromagneticw0000wait) |
| Orfanidis, *Electromagnetic Waves and Antennas*, Rutgers University | Multilayer dielectric reflection/transmission via impedance recursion (ch. 4 in the cited draft) | [ece.rutgers.edu/~orfanidi/ewa](https://www.ece.rutgers.edu/~orfanidi/ewa/) |

## License

MIT License. See `LICENSE`.

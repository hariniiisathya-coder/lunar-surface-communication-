# Task Breakdown — Lunar Comms Summer Internship 2026

Three students, 8–10 weeks, one shared scenario:
**a 5G BTS at Connecting Ridge (lunar south pole) + LCRNS/Moonlight relay in ELFO + Earth DSN.**

Each student owns one track. All three share Weeks 0–1 (common context) and
contribute to the same repository. See `README.md` for the repo structure.

---

## Shared — Week 0 (Days 1–5): Common ground

**All three students together.**

| Day | Activity |
|-----|----------|
| 1 | Read NASA Moon Fact Sheet + Wikipedia "Orbit of the Moon". Calculate Earth-Moon delay and radio horizon by hand. |
| 2 | Open LROC QuickMap ([quickmap.lroc.asu.edu](https://quickmap.lroc.asu.edu)). Identify Connecting Ridge, Shackleton crater, de Gerlache. Write 1-page "what I see" summary. |
| 3 | Read Edwards et al. (2023) NTRS 20220015268 ("3GPP Telecommunications Technology on the Moon"). Identify the three main simplifying assumptions the paper makes. |
| 4 | Install environment: `conda env create -f environment.yml && pip install -e ".[dev]"`. Run `pytest tests/ -v` → all tests should raise `NotImplementedError` (that is expected and correct). |
| 5 | Draw the shared scenario diagram (see README) on a whiteboard. Each student explains their track to the other two. |

**Deliverable:** 1 page per student explaining the shared scenario and where their track fits.

---

## Student 1 — Surface RF Propagation + Coverage Maps

**Track owner:** Student 1
**Modules:** `lunarcomms/regolith/`, `lunarcomms/propagation/`, `lunarcomms/geometry/horizon.py`, `lunarcomms/coverage/`, `lunarcomms/io/`
**Survey chapters:** `docs/survey/03-rf-propagation.md`, `docs/survey/04-regolith-dielectrics.md`
**Final deliverable:** Six GeoTIFF coverage maps (3 bands × surface + terrain scenarios), uncertainty analysis, paper draft.

---

### S1-W1 — Background reading (Week 1)

Read in order:

1. **Link budget basics** — Rappaport (1996) *Wireless Communications*, Sections 3.1–3.5.
   (Available via university library; covers Friis, two-ray, and diffraction.)

2. **Regolith dielectrics** — Olhoeft & Strangway (1975), full paper.
   Open access via NASA ADS: https://ui.adsabs.harvard.edu/abs/1975E%26PSL..24..394O/abstract

3. **Modern loss tangent** — Siegler et al. (2020), Sections 1–3 and Figure 4.
   Open access: https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2020JE006405

4. **Methodology reference** — Toonen et al. (2022) IEEE JRFID, doi:10.1109/JRFID.2022.3159775.
   Read Sections I-III for context on SBR ray-tracing over LOLA DEM, and Fig. 6 for L99% fade-loss
   maps at the south pole. This paper optimises ray-tracing efficiency; your two-ray + Deygout model
   is a simpler analytical complement. Use their L99% maps as a qualitative sanity check.

5. **What you need to improve** — Edwards et al. (2023) NTRS 20220015268, Table III and IV.
   Note: uses εr=3.0, tan δ=0, no terrain. You will fix all three.

**Write:** a 1-page table of "assumptions made in each paper" vs "what this repo does differently."

---

### S1-W2 — First module: regolith dielectric (Week 2)

**Files to implement:**
- `lunarcomms/regolith/dielectric.py` — all 5 functions
- `lunarcomms/io/pgda.py` — `load_dem()` only

**Steps:**
1. Implement `permittivity()` — formula in module docstring. 1 line of code.
2. Implement `loss_tangent()` — formula in module docstring. 1 line of code.
3. Implement `complex_permittivity()` — calls the two above. 1 line.
4. Implement `skin_depth_m()` — formula in module docstring.
5. Run `pytest tests/test_regolith.py -v`. All `TestPermittivity` and `TestLossTangent` tests must pass.
6. Download PGDA-78 DEM: `python data/download_pgda.py --product 78`
7. Implement `load_dem()` using rasterio. Verify data.shape is sensible.
8. Plot a 40-km clip of the DEM in QGIS or matplotlib. Annotate Shackleton and Connecting Ridge.

**Acceptance criteria:**
- `pytest tests/test_regolith.py` → 0 failures (excluding `TestFresnelCoefficients` which is Week 3).
- A notebook `notebooks/05-regolith-dielectric-map.ipynb` with a plot of tan δ vs frequency for 3 density values.

**Key number to report:** How much does tan δ = 0 (Edwards 2023 assumption) underestimate path loss at S-band? Compute for ρ=1.50 g/cm³ at 2.5 GHz, 10 km path, using skin depth as a reference.

---

### S1-W3 — Fresnel coefficients + SPICE geometry (Week 3)

**Files:**
- `lunarcomms/regolith/dielectric.py` — `fresnel_coefficients()`
- `lunarcomms/geometry/frames.py` — `load_kernels()`, `earth_moon_distance_km()`

**Steps:**
1. Implement `fresnel_coefficients()` — formulas in docstring. ~5 lines.
2. Plot |Γ_v| and |Γ_h| vs grazing angle from 0° to 90° at S-band.
   Verify: near 0°, both approach 1. Near 58.5°, |Γ_v| has a minimum (Brewster angle).
3. Run `pytest tests/test_regolith.py::TestFresnelCoefficients`.
4. Download SPICE kernels: `python data/download_kernels.py`
5. Implement `load_kernels()` and `earth_moon_distance_km()`.
6. Run `pytest tests/test_geometry.py::TestEarthMoonDistance`.

**Acceptance criteria:**
- `pytest tests/test_regolith.py` → all passing.
- Earth-Moon distance verified against JPL Horizons for 2026-Jan-01 (see test docstring).

---

### S1-W4 — Friis + two-ray model (Week 4)

**Files:**
- `lunarcomms/propagation/friis.py` — all functions
- `lunarcomms/propagation/two_ray.py` — `breakpoint_distance()`, `path_loss_db()`
- `lunarcomms/geometry/horizon.py` — `los_mask_from_tx()`

**Steps:**
1. Implement `friis.fspl_db()`, `received_power_dbm()`, `link_margin_db()`, `max_range_m()`.
2. Reproduce the Friis-only link budget from Edwards (2023) Section IV using the parameters stated in
   the paper. Check that your `max_range_m()` output matches their stated coverage radius.
3. Implement `breakpoint_distance()`. Verify the S-band breakpoint is ~2 km.
4. Implement `two_ray.path_loss_db()` with complex exponentials (not the far-field approximation).
5. Plot Friis vs two-ray path loss from 100 m to 20 km at S-band (hT=30m, hR=2m).
   You should see: oscillations near the transmitter, then divergence beyond 2 km.
6. Implement `los_mask_from_tx()`. Test on flat DEM (`test_geometry.py::TestHorizonMask`).
7. Run `pytest tests/test_propagation.py -v`.

**Acceptance criteria:**
- `pytest tests/test_propagation.py` → all passing.
- Plot showing two-ray vs Friis divergence, annotated with breakpoint distance.

---

### S1-W5 — Diffraction + first coverage map (Week 5)

**Files:**
- `lunarcomms/propagation/diffraction.py` — all functions
- `lunarcomms/io/pgda.py` — `extract_profile()`
- `lunarcomms/coverage/link_budget.py` — `compute_coverage_map()`

**Steps:**
1. Implement `fresnel_kirchhoff_parameter()` and `knife_edge_loss_db()`.
2. Implement `deygout_loss_db()` for up to 3 edges.
3. Test single-edge case: verify Deygout matches `knife_edge_loss_db()` exactly.
4. Implement `extract_profile()` using `scipy.ndimage.map_coordinates`.
5. Implement `compute_coverage_map()` — combine LOS mask + two-ray + Deygout.
6. Run on a 40-km DEM clip centred on Connecting Ridge. BTS at Connecting Ridge crest.
   Produce `coverage_S_2500MHz_margin.tif`.
7. Overlay coverage map on DEM in QGIS. Annotate Shackleton, PSRs, candidate landing sites.

**Acceptance criteria:**
- `pytest tests/test_propagation.py::TestDiffraction` → all passing.
- First S-band coverage GeoTIFF produced and viewable in QGIS.
- Link margin > 0 dB for at least 50% of the area within 5 km of BTS.

---

### S1-W6 — Multi-band maps + GeoTIFF output (Week 6)

**Files:**
- `lunarcomms/coverage/link_budget.py` — `save_coverage_geotiff()`

**Steps:**
1. Implement `save_coverage_geotiff()` with rasterio.
2. Run `compute_coverage_map()` for all three bands: UHF (442.5 MHz), S (2.5 GHz), Ka (27 GHz).
3. Produce six GeoTIFFs (LOS mask + margin for each band).
4. Create comparison figure: side-by-side coverage maps, three bands.
5. Compute key statistics: coverage area (km²) at margin > 0 dB for each band.

**Key result to report:**
Compare your terrain-aware S-band coverage radius against the Friis-only result from Edwards (2023)
Section IV. The terrain-aware result should be substantially smaller for typical south-pole morphology.

---

### S1-W7–8 — Spatial regolith variation + uncertainty (Weeks 7–8)

**Files:**
- `lunarcomms/io/pgda.py` — `sample_loss_tangent_params()`
- `lunarcomms/propagation/two_ray.py` — `path_loss_spatial_db()`

**Steps:**
1. Download Siegler (2020) loss-tangent parameter maps from Zenodo:
   https://zenodo.org/records/3993798
   Files: "Figure 11_Constant Loss Parameter_a'.txt" and "Figure 11_Frequency Exponent_b'.txt"
2. Implement `sample_loss_tangent_params()` — interpolate a'(lon,lat) and b'(lon,lat) to
   the PGDA-78 pixel grid (nearest-neighbour at ~8 km native resolution is sufficient).
3. Implement `path_loss_spatial_db()` — use spatially varying tan_delta = a' * f**b'.
4. Rerun coverage maps with spatially varying tan δ.
5. Monte Carlo uncertainty analysis (N=100 runs):
   - Perturb a' ± 30%, b' ± 0.1 (Siegler 2020 stated uncertainty on retrieved parameters).
   - Report 5th–95th percentile band on coverage area.

**Deliverable:** Uncertainty-quantified coverage maps. This is what makes the paper publishable —
no existing lunar coverage paper includes this.

---

### S1-W9–10 — Paper draft (Weeks 9–10)

**Survey chapter to write:** `docs/survey/03-rf-propagation.md` and `docs/survey/04-regolith-dielectrics.md`

**Paper structure (IEEE Aerospace / WiSEE):**
1. Introduction — why terrain-aware, uncertainty-quantified lunar coverage matters.
2. Propagation model — two-ray + Deygout, with lunar regolith physics.
3. DEM and dielectric data — PGDA-78, Siegler 2020, validation.
4. Coverage results — 3 bands, comparison with Edwards (2023) Friis baseline and Toonen et al. (2022) L99% ray-tracing maps.
5. Uncertainty analysis — Monte Carlo results.
6. Conclusions.

**Target venues:** IEEE WiSEE 2026, IEEE Aerospace 2026, or Acta Astronautica.

---

## Student 2 — 3GPP/5G Stack Adaptation for the Moon

**Track owner:** Student 2
**Modules:** `lunarcomms/orbits/elfo.py`, `lunarcomms/geometry/frames.py`
**Survey chapters:** `docs/survey/02-relay-architectures.md`, `docs/survey/05-3gpp-on-the-moon.md`
**Final deliverable:** Layer-by-layer 3GPP "lunar readiness" table + Doppler/delay analysis + paper draft.

---

### S2-W1 — Background reading (Week 1)

1. **5G architecture** — 3GPP TS 38.300 v17.x, Section 4 (NR architecture overview).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.300/

2. **NTN fundamentals** — 3GPP TR 38.811 v15.4, Sections 5–6 (NTN channel model, LEO/GEO).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.811/

3. **NTN system design** — 3GPP TR 38.821 v16.x, Section 6 (solutions for NR NTN).
   Specifically: Section 6.2 (timing), 6.3 (HARQ), 6.4 (PRACH).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.821/

4. **Lunar 5G baseline** — Edwards et al. (2023), NTRS 20220015268
   ("3GPP Telecommunications Technology on the Moon"). Read Sections III-IV (link budget and coverage).

5. **LunaNet AFS** — LunaNet Interoperability Specification v5, Section 3.2.
   (AFS frequency 2492.028 MHz and its proximity to 3GPP SFCGb1 band.)
   NASA NTRS: https://ntrs.nasa.gov/citations/20220010064

---

### S2-W2 — ELFO geometry: Doppler and delay (Week 2)

**Goal:** Understand quantitatively why ELFO Doppler and delay differ from LEO.

**Steps:**
1. Read 3GPP TR 38.821, Table 6.1.3-1: LEO-600 reference scenario Doppler ±24 kHz, delay 1.5–5 ms.
2. For LCRNS-1 ELFO (a=5500 km, e=0.60, i=57.7°, w=90°, from `data/orbits/lcrns_ref_constellation.json`):
   - v_peri = sqrt(mu*(1+e)/(a*(1-e))) = sqrt(4902.8*1.6/(5500*0.4)) ≈ 1.89 km/s
   - v_apo  = sqrt(mu*(1-e)/(a*(1+e))) = sqrt(4902.8*0.4/(5500*1.6)) ≈ 0.47 km/s
3. With w=90°, apolune is over the south pole — the contact window IS the apolune arc.
   Max Doppler during the contact window at S-band (2.5 GHz):
   - Apolune (visible from south pole): Df_max = v_apo/c * f = (470/3e5) * 2.5e9 ≈ 3.9 kHz
   - Perilune (NOT visible from south pole for w=90°): Df_max ≈ 15.8 kHz — for comparison only.
4. One-way delay during contact window:
   - Apolune altitude = a*(1+e) - R_Moon = 8800 - 1737 = 7063 km → tau = 7063/3e5 ≈ 23.5 ms
5. Compare against 3GPP TR 38.821 LEO-600 baseline. Write a table.

**Key finding:** During contact windows (satellite near apolune), Doppler is ~3.9 kHz and delay is
~23.5 ms. The 3.9 kHz Doppler exceeds the 10%-of-SCS threshold for SCS 15 kHz (1.5 kHz) and SCS
30 kHz (3.0 kHz); SCS 60 kHz (threshold 6.0 kHz) is the minimum viable option. The 23.5 ms
one-way delay gives HARQ RTT ~47 ms vs the default 4 ms NR value. 3GPP NTN was designed for
LEO (Doppler always >10 kHz, delay <5 ms); the lunar ELFO regime is fundamentally different.

---

### S2-W3 — Implement ELFO propagator (Week 3)

**Files:** `lunarcomms/orbits/elfo.py` — `keplerian_state()`, `propagate_elfo()`, `south_pole_elevation_deg()`

**Steps:**
1. Implement `keplerian_state()` — Keplerian → Cartesian. See Bate et al. (1971) Section 2.4.
2. Implement `propagate_elfo()` — solve Kepler's equation with Newton-Raphson (≤ 10 iterations).
3. Implement `south_pole_elevation_deg()`.
4. Run `pytest tests/test_geometry.py::TestELFOGeometry`.
5. Propagate for 48 h. Plot elevation angle from south pole vs time.
   - You should see 4–5 peaks per 48 h (one per 10-h orbit), each lasting ~7–8 h above 5°.
   - Compare against LCRNS Reference Constellation 3.1 (NTRS 20250002698), Figure 3.

**Acceptance criteria:**
- `pytest tests/test_geometry.py::TestELFOGeometry` → all passing.
- Elevation plot matches NTRS 20250002698 Fig. 3 qualitatively.

---

### S2-W4 — PHY layer analysis: SCS suitability and HARQ timer analysis (Week 4)

**Goal:** Identify which 3GPP NR subcarrier spacings and timer settings are viable under lunar ELFO Doppler and delay, compared to the 3GPP TR 38.821 LEO-600 baseline.

**Steps:**
1. Extract Doppler time series from your ELFO propagator:
   - Radial velocity = d/dt(|position|). Convert to frequency offset: Δf = v_radial/c · f.
2. Analyse per 3GPP TR 38.821, Section 6.2.1:
   - Which subcarrier spacings (SCS 15 / 30 / 60 kHz) can tolerate Δf from Step 1?
   - Rule: acceptable Doppler offset < 10% of SCS (3GPP RAN4 guideline).
   - During contact window (apolune, Df≈3.9 kHz):
     SCS 15 kHz → failure (3.9 > 1.5 kHz threshold).
     SCS 30 kHz → failure (3.9 > 3.0 kHz threshold).
     SCS 60 kHz → OK (3.9 < 6.0 kHz threshold) — minimum viable SCS for lunar ELFO.
3. Analyse HARQ RTT:
   - With slant range 7000 km (apolune): RTT = 2 · 23 ms = 46 ms.
   - 3GPP NR default HARQ RTT for TDD = 8 slots = 4 ms @ SCS 15 kHz.
   - How many retransmissions can fit in one contact window (7 h)?
   - Document the HARQ timer breakage in a table.
4. Analyse T300 / T310 timers (RRC Connection Request):
   - T300 default = 1000 ms. One-way delay to 5GC on Earth = 1280 ms. T300 expires before response arrives.
   - Resolution: local 5GC at lander. Document architectural requirement.

**Deliverable:** A table "3GPP NR Rel-17 Lunar Readiness" with columns:
  Layer | Parameter | LEO-600 (TR 38.821) | ELFO Apolune | ELFO Perilune | Verdict (✓/⚠/✗)

This table is the main contribution of Track S2.

---

### S2-W5 — Frequency coexistence: LunaNet AFS vs 3GPP SFCGb1 (Week 5)

**Goal:** Assess interference between LunaNet AFS (2492.028 MHz) and 3GPP SFCGb1 (2503.5–2655 MHz).

**Steps:**
1. Read SFCG Recommendation 32-2R5 (Space Frequency Coordination Group, lunar bands).
   Available: https://www.sfcg.org/documents/sfcg32-2r5.pdf
2. Compute the guard band: 2503.5 − 2492.028 = 11.472 MHz.
3. Compute the ACS (Adjacent Channel Selectivity) requirement for NR at 2503.5 MHz:
   - 3GPP TS 38.101-1, Table 7.3.3-1 (ACS for FR1). ACS ≥ 33 dB.
4. Estimate whether a 11.472 MHz guard band is sufficient given the AFS signal bandwidth (2.048 MHz).
5. Propose the minimum guard band needed and check against SFCG allocation.

**Deliverable:** A 1-page coexistence analysis with a spectrum diagram showing AFS and SFCGb1.
This feeds into Section V of the Track S2 paper.

---

### S2-W6–8 — Surface-to-ELFO link budget using S1 coverage output (Weeks 6–8)

**Collaboration with S1.** Use the coverage GeoTIFFs produced by Student 1 to add
the surface→relay dimension to your analysis.

**Steps:**
1. From S1's LOS mask, extract which fraction of the south-pole area has LOS to ELFO relay
   during the contact window (elevation ≥ 5°).
2. Compute end-to-end link budget: surface BTS → relay → Earth DSN.
   Parameters: BTS EIRP = 53 dBm, relay gain per LCRNS SRD (NTRS 20250002698 Table 2).
3. Map: for each surface pixel in LOS of relay, what is the received SNR at the DSN?

---

### S2-W9–10 — Paper draft (Weeks 9–10)

**Survey chapter to write:** `docs/survey/05-3gpp-on-the-moon.md`

**Paper structure:**
1. Introduction — why 3GPP NTN was designed for LEO and what breaks on the Moon.
2. ELFO geometry — Doppler and delay time series, comparison with TR 38.821.
3. PHY layer — SCS selection, BLER vs Doppler, frequency coexistence.
4. MAC/RRC layer — HARQ RTT, timer breakage, 5GC placement.
5. Conclusions and recommendations for a 3GPP Release targeting lunar operations.

**Target venues:** IEEE Globecom NTN Workshop, IEEE Aerospace, or IEEE Communications Magazine.

---

## Student 3 — DTN / Delay-Tolerant Networking for the Solar System Internet

**Track owner:** Student 3
**Modules:** `lunarcomms/orbits/lcrns.py` (contact plan export)
**Survey chapters:** `docs/survey/06-dtn-and-solar-system-internet.md`
**Final deliverable:** Public benchmark suite (contact plans + router comparison table) + tool paper.

---

### S3-W1 — Background reading (Week 1)

1. **DTN introduction** — CCSDS 734.2-B-2 (Bundle Protocol v7), Sections 1–3.
   Free download: https://public.ccsds.org/Pubs/734x2b2.pdf

2. **Contact Graph Routing** — CCSDS 734.3-B-1 (SABR), Sections 1–4.
   Free download: https://public.ccsds.org/Pubs/734x3b1.pdf

3. **ION-DTN tutorial** — NASA NTRS 20190034046 (ION Developer Course Materials).
   https://ntrs.nasa.gov/citations/20190034046

4. **DSNS simulator** — Read the paper: ssloxford/DSNS on arXiv: 2508.04317.
   Then install: `pip install dsns` (if published) or clone from https://github.com/ssloxford/DSNS

5. **LunaNet DTN requirement** — LunaNet ICD v5, Section 4.1 (LunaNet requires BPv7).
   NASA NTRS: https://ntrs.nasa.gov/citations/20220010064

6. **Why this is a gap** — Search GitHub for "LCRNS contact plan" and "Moonlight contact plan."
   You will find nothing. This is the contribution.

---

### S3-W2 — Understand and run DSNS (Week 2)

**Steps:**
1. Clone DSNS: `git clone https://github.com/ssloxford/DSNS`
2. Run the included example (CCSDS reference scenario from the paper).
3. Reproduce Table 1 of the DSNS paper: bundle delivery ratio for CGR vs epidemic.
4. Understand the contact plan format: CSV with columns start_time, end_time, from_node, to_node, rate_bps, owlt_s.
5. Write a minimal contact plan for a toy scenario:
   - 1 surface node, 1 relay, contact window of 4 h at rate 1 Mbps, OWLT 23 ms.
   - Run CGR over it. Verify delivery ratio = 1.0 for a 1-bundle transmission.

**Deliverable:** A notebook `notebooks/03-propagate-lcrns-elfo.ipynb` stub with DSNS import working.

---

### S3-W3 — LCRNS ELFO propagation + contact windows (Week 3)

**Files:**
- `lunarcomms/orbits/elfo.py` — `contact_windows()` (implement after S2-W3)
- `lunarcomms/geometry/frames.py` — `earth_elevation_angle_deg()`

**Coordinate with Student 2** to reuse the `propagate_elfo()` implementation.

**Steps:**
1. Propagate the 2-satellite LCRNS constellation (elements from `data/orbits/lcrns_ref_constellation.json`)
   over 7 days (one week).
2. Compute elevation from south pole for each satellite at each time step.
3. Use `contact_windows()` to extract contact windows (min elevation = 5°).
4. Compute: how often is at least one satellite visible? (Target: ≥ 95% per NTRS 20250002698 Table 5.)
5. Also compute: how long is the Earth direct-to-surface link available?
   (Use `earth_elevation_angle_deg()` — Earth must be above 5° elevation AND terrain-unobstructed.)

**Acceptance criteria:**
- A 7-day contact window table (CSV): start, end, satellite, duration.
- 2-sat coverage fraction ≥ 95% at south pole (validate against NTRS 20250002698).

---

### S3-W4 — Contact plan generator (Week 4)

**File:** `lunarcomms/orbits/lcrns.py` — `export_contact_plan()`

This is the **publishable gap** in the community. No public contact plan generator exists for
the LCRNS/Moonlight constellation as of June 2025.

**Steps:**
1. Implement `export_contact_plan()` — convert contact windows to ION-DTN ionrc format.
2. Also export in DSNS CSV format (both formats, one function with a `format` parameter).
3. Include OWLT per contact (compute from satellite-surface distance at window midpoint).
4. Validate: load the exported contact plan into DSNS and run a simple bundle transfer.
   Verify delivery ratio = 1.0 for a bundle sent during a contact window.

**Deliverable:** `data/orbits/lcrns_2sat_7day_contact_plan.csv` — a ready-to-use file
for any DTN researcher studying lunar scenarios. Commit this file to the repo.

---

### S3-W5 — Router benchmark: CGR vs SABR vs epidemic (Week 5)

**Steps:**
1. Using the LCRNS 7-day contact plan, define three traffic profiles:
   - **Rover telemetry** (steady): 10 kbps constant, bundle size 1 MB, TTL 48 h.
   - **EVA video** (bursty): 1 Mbps for 30 min during EVA, then silent, bundle 100 MB, TTL 2 h.
   - **Emergency science** (low-priority): 100 kbps, preemptable by EVA traffic, TTL 7 days.

2. Run each router (CGR, SABR, epidemic) over each traffic profile using DSNS.
   - Enable and disable custody transfer to see the effect.

3. Collect metrics:
   - Bundle Delivery Ratio (BDR)
   - 95th percentile end-to-end delay
   - Peak buffer usage at relay (bytes)
   - Number of retransmissions

4. Build the comparison table. This is Table I of your paper.

**Acceptance criteria:** A 3×3 table (3 routers × 3 traffic profiles) with all 4 metrics filled.

---

### S3-W6 — Stretch: Solar System Internet (Week 6)

**Steps:**
1. Add a Mars relay node to the contact plan:
   - Earth-Mars one-way light time: 3–22 min (varies with orbital phase).
   - Mars DSN window: 8 h/day (approximate for a single ground station).
   - Use hapsira (active poliastro fork, archived Oct 2023) to compute Earth-Mars distance:
     `pip install hapsira`
2. Re-run CGR benchmark with the extended scenario (Moon → Earth → Mars relay chain).
3. Observe where CGR fails (storage overflow at Earth relay, routing loops when contact
   plans extend beyond the horizon).
4. Document the failure mode in the survey chapter. This identifies an open research problem.

---

### S3-W7–8 — Package the tool (Weeks 7–8)

**Steps:**
1. Clean up `export_contact_plan()` with docstrings and error handling.
2. Add a command-line interface:
   ```bash
   python -m lunarcomms.orbits.lcrns --start 2026-01-01 --duration 30d --format ion > contact.ionrc
   ```
3. Write the tool documentation in `docs/tutorials/contact-plan-generator.md`.
4. Test on at least two independent scenarios (1-sat and 2-sat constellations).

**Target for tool paper:** JOSS (Journal of Open Source Software) or SoftwareX.
These are short (~5 page) papers for software artifacts with a code review.
JOSS: https://joss.theoj.org/   SoftwareX: https://www.sciencedirect.com/journal/softwarex

---

### S3-W9–10 — Paper draft (Weeks 9–10)

**Survey chapter to write:** `docs/survey/06-dtn-and-solar-system-internet.md`

**Paper structure:**
1. Introduction — why a public lunar DTN benchmark is needed.
2. The LCRNS contact plan generator — how it works, parameters, validation.
3. Router benchmark — CGR vs SABR vs epidemic on three traffic profiles.
4. Solar System Internet extension — where CGR scales and where it breaks.
5. Conclusions.

**Target venues:** IEEE Aerospace 2026, AIAA SPACE, or IEEE Globecom Space Comms workshop.

---

## Shared — Week 9–10: Integration and demo

All three students run the end-to-end pipeline:

```
S1 GeoTIFF (coverage map)
   → link_closes[pixel] = margin_map > 0
S2 ELFO elevation (contact availability)
   → relay_visible[t] = elevation_deg > 5
S3 Contact plan (DTN delivery)
   → bundle_delivered = CGR(contact_plan, traffic)
```

**Joint deliverable:**
A single Jupyter notebook `notebooks/07-first-link-budget.ipynb` that:
1. Loads S1's S-band coverage GeoTIFF.
2. Overlays S2's ELFO contact windows.
3. Runs one bundle delivery simulation in DSNS using S3's contact plan.
4. Reports: for a rover at a random south-pole location, what fraction of science data
   generated in a 7-day period is delivered to Earth DSN?

This is the end-to-end demonstration that connects all three tracks into a single result.

---

## Open issues (for GitHub Issues tracker)

| # | Description | Assigned | Week |
|---|-------------|----------|------|
| 1 | Implement all `dielectric.py` functions | S1 | W2 |
| 2 | Implement Friis + two-ray + diffraction | S1 | W3–4 |
| 3 | Implement horizon raycasting (vectorised) | S1 | W4 |
| 4 | Implement `compute_coverage_map()` + GeoTIFF output | S1 | W5–6 |
| 5 | Implement `load_dem()` + `extract_profile()` + `sample_density()` | S1 | W2–5 |
| 6 | Implement `keplerian_state()` + Kepler equation solver | S2/S3 | W3 |
| 7 | Implement `propagate_elfo()` + `south_pole_elevation_deg()` | S2/S3 | W3 |
| 8 | Implement `load_lcrns_elements()` + `coverage_fraction()` | S2/S3 | W4 |
| 9 | 3GPP NR Rel-17 lunar readiness table (PHY + MAC + RRC) | S2 | W4–5 |
| 10 | Implement `contact_windows()` + `export_contact_plan()` | S3 | W4 |
| 11 | Run CGR/SABR/epidemic benchmark on LCRNS contact plan | S3 | W5 |
| 12 | Write survey chapter `03-rf-propagation.md` | S1 | W9 |
| 13 | Write survey chapter `05-3gpp-on-the-moon.md` | S2 | W9 |
| 14 | Write survey chapter `06-dtn-and-solar-system-internet.md` | S3 | W9 |
| 15 | Monte Carlo uncertainty on coverage maps | S1 | W7–8 |
| 16 | Solar System Internet stretch (Mars relay) | S3 | W6 |
| 17 | End-to-end integration notebook | All | W10 |
| 18 | Add `references.bib` entries for all cited papers | All | ongoing |

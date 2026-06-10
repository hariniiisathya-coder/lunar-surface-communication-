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
| 3 | Read Edwards et al. (2023) NTRS 20220015268 ("3GPP Mobile Telecommunications Technology on the Moon"). Identify the three main simplifying assumptions the paper makes. |
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

## Student 2 — Assessment of 5G Integration with DTN/CCSDS Using ELFO Relay Satellites

**Track owner:** Student 2
**Nature of the track:** This is a **protocol feasibility study**, not an implementation track.
The contribution is an in-depth analysis of the 3GPP NR/NTN protocol stack: which procedures,
timers, and assumptions break under lunar ELFO conditions, what modifications would be required,
the justification for each, and how 5G can be made compatible with DTN/CCSDS for the three
integration options. All orbital geometry inputs (Doppler/delay time series, contact windows)
are consumed from Student 3's propagator outputs — Student 2 does not write simulation code.
**Survey chapters:** `docs/survey/02-relay-architectures.md`, `docs/survey/05-3gpp-on-the-moon.md`
**Research question:** How should the 5G RAN integrate with DTN/CCSDS when ELFO satellites
provide intermittent backhaul — and at which point in the 5G stack should DTN sit?
Which 3GPP procedures must be modified for feasibility, and with what justification?
**Integration options under study:**
  (A) DTN above the UPF (full 5G Core retained),
  (B) DTN after the gNB (reduced Core dependency),
  (C) local lunar 5G Core with DTN backhaul to Earth.
**Payload options under study:** transparent (bent-pipe) vs. regenerative ELFO relay.
**Final deliverable:** Architectural trade-off analysis (3 DTN integration points × 2 payload
types), 3GPP "lunar readiness" table, and paper draft with architectural recommendations.

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

4b. **Updated 5G lunar study** — Wagner et al. (2025), NTRS 20250001947
    ("Envisioned Lunar Surface Comms Using 3GPP Cellular and Wi-Fi Technologies").
    Companion to Edwards 2023; covers Artemis V multi-rover scenario, SWaP, Nokia/Axiom spacesuit
    integration. Read alongside item 4 — this is the most current NASA Glenn assessment.

5. **LunaNet AFS** — LunaNet Interoperability Specification v5, Section 3.2.
   (AFS frequency 2492.028 MHz and its proximity to 3GPP SFCGb1 band.)
   NASA NTRS: https://ntrs.nasa.gov/citations/20230012811

6. **DTN fundamentals** — CCSDS 734.2-B-2 (Bundle Protocol v7), Sections 1–3.
   Free download: https://public.ccsds.org/Pubs/734x2b2.pdf
   (Coordinate with Student 3 — this is their core spec. You need it to reason about
   where BPv7 attaches to the 5G stack.)

7. **5G system architecture** — 3GPP TS 23.501 v17.x, Section 4.2.
   Focus on the user-plane path (UE → gNB → UPF → N6 interface) and the control-plane
   functions (AMF/SMF). You must be able to draw where user traffic exits the 5G system —
   that is where DTN integration options A and B differ.

8. **LCRNS system overview** — Esper et al. (2025), NTRS 20250003321, SpaceOps 2025 paper #257.
   System-level LCRNS context: commercial payload strategy, constellation coverage, and
   bent-pipe vs. regenerative trade-offs from the programme office perspective.
   https://ntrs.nasa.gov/citations/20250003321

9. **3GPP Rel-19 NTN** — 3GPP Release 19 (completed Dec 2025).
   NR_NTN_Ph3 work item on regenerative vs. transparent payload architecture for GEO/NGSO.
   https://www.3gpp.org/specifications-technologies/releases/release-19

10. **µD3TN DTN stack** — Wischer et al. (2024), arXiv:2407.17166.
    Modular BPv7 software stack with CCSDS SPP convergence layer. Relevant for
    understanding how to implement the CL adapter between gNB/UPF and the DTN node.
    Open-source: https://gitlab.com/d3tn/ud3tn

---

### S2-W2 — ELFO geometry: Doppler and delay (Week 2)

**Goal:** Understand quantitatively why ELFO Doppler and delay differ from LEO.

**Steps:**
1. Read 3GPP TR 38.821, Table 6.1.3-1: LEO-600 reference scenario Doppler ±24 kHz, delay 1.5–5 ms.
2. For LCRNS SV-1 ELFO (a=11315.936 km, e=0.691982, i=59.37°, w=92.49°≈90°, from `data/orbits/lcrns_ref_constellation.json`):
   - v_peri = sqrt(mu*(1+e)/(a*(1-e))) = sqrt(4902.8*1.691982/(11315.936*0.308018)) ≈ 1.54 km/s
   - v_apo  = sqrt(mu*(1-e)/(a*(1+e))) = sqrt(4902.8*0.308018/(11315.936*1.691982)) ≈ 0.28 km/s
3. With w=90°, apolune is over the south pole — the contact window IS the apolune arc.
   Max Doppler during the contact window at S-band (2.5 GHz):
   - Apolune (visible from south pole): Df_max = v_apo/c * f = (280/3e5) * 2.5e9 ≈ 2.3 kHz
   - Perilune (NOT visible from south pole for w=90°): Df_max ≈ 12.8 kHz — for comparison only.
4. One-way delay during contact window:
   - Apolune altitude = a*(1+e) - R_Moon = 11315.936*1.691982 - 1737.4 = 17395 km → tau = 17395/3e5 = 58 ms
5. Compare against 3GPP TR 38.821 LEO-600 baseline. Write a table.

**Key finding:** During contact windows (satellite near apolune), Doppler is ~2.3 kHz and delay is
~58 ms. The 2.3 kHz Doppler exceeds the SCS 15 kHz threshold (1.5 kHz) but is below the SCS
30 kHz threshold (3.0 kHz); SCS 30 kHz is the minimum viable option. The 58 ms one-way delay
gives HARQ RTT ~116 ms vs the default 4 ms NR value — a 29x increase. 3GPP NTN was designed for
LEO (delay <5 ms); the lunar ELFO delay regime is dominated by altitude, not Doppler.

---

### S2-W3 — Protocol deep-dive: NR/NTN procedure inventory (Week 3)

**Goal:** Build a systematic inventory of every 3GPP NR procedure and parameter that depends on
terrestrial assumptions (delay, Doppler, continuous connectivity) and classify each as
works-as-is / needs reconfiguration / needs specification change for the lunar ELFO scenario.

**Note:** the ELFO propagator is implemented by Student 3 (S3-W3, shared issue #6–7).
Request the Doppler/delay time series and contact window table from Student 3 — your work
starts from those numbers, not from code.

**Steps:**
1. Go through 3GPP TS 38.300 + TR 38.821 and list every procedure touched by NTN Rel-17:
   timing advance (TA), HARQ, scheduling offsets (K_offset), RACH/PRACH, RLC/PDCP timers,
   RRC timers (T300/T301/T310/T311), cell selection/reselection, paging, TAU.
2. For each procedure, record: terrestrial assumption → Rel-17 NTN extension (GEO max
   ~270 ms) → lunar ELFO requirement (from S3's geometry) → gap.
3. Identify which gaps are solvable by configuration (e.g., extended K_offset values) vs.
   which require specification changes (e.g., timer ranges that max out below lunar delay)
   vs. which require architectural workarounds (e.g., local 5GC — feeds S2-W7).
4. Document the justification for each proposed modification, citing the exact spec clause.

**Deliverable:** "NR/NTN procedure inventory" table — the backbone of the lunar readiness
table (S2-W4) and the architectural analysis (S2-W7). Each row: procedure, spec clause,
terrestrial/NTN assumption, lunar value, verdict, required modification, justification.

---

### S2-W4 — PHY layer analysis: SCS suitability and HARQ timer analysis (Week 4)

**Goal:** Identify which 3GPP NR subcarrier spacings and timer settings are viable under lunar ELFO Doppler and delay, compared to the 3GPP TR 38.821 LEO-600 baseline.

**Steps:**
1. Obtain the Doppler time series from Student 3's ELFO propagator output:
   - Radial velocity = d/dt(|position|). Convert to frequency offset: Δf = v_radial/c · f.
2. Analyse per 3GPP TR 38.821, Section 6.2.1:
   - Which subcarrier spacings (SCS 15 / 30 / 60 kHz) can tolerate Δf from Step 1?
   - Rule: acceptable Doppler offset < 10% of SCS (3GPP RAN4 guideline).
   - During contact window (apolune, Df≈2.3 kHz):
     SCS 15 kHz → failure (2.3 > 1.5 kHz threshold).
     SCS 30 kHz → OK (2.3 < 3.0 kHz threshold) — minimum viable SCS for lunar ELFO.
     SCS 60 kHz → easily OK.
3. Analyse HARQ RTT:
   - With slant range 17400 km (apolune): RTT = 2 · 58 ms = 116 ms.
   - 3GPP NR default HARQ RTT for TDD = 8 slots = 4 ms @ SCS 15 kHz.
   - How many retransmissions can fit in one contact window (~15–20 h above 5°)?
   - Document the HARQ timer breakage in a table.
4. Analyse T300 / T310 timers (RRC Connection Request):
   - T300 default = 1000 ms. One-way delay to 5GC on Earth = 1280 ms. T300 expires before response arrives.
   - Resolution: local 5GC at lander. Document architectural requirement.

**Deliverable:** A table "3GPP NR Rel-17 Lunar Readiness" with columns:
  Layer | Parameter | LEO-600 (TR 38.821) | ELFO Apolune | ELFO Perilune | Verdict (✓/⚠/✗)

This table feeds the payload comparison (S2-W6) and the DTN integration trade-off (S2-W7) —
together they form the main contribution of Track S2.

---

### S2-W5 — Frequency coexistence: LunaNet AFS vs 3GPP SFCGb1 (Week 5)

**Goal:** Assess interference between LunaNet AFS (2492.028 MHz) and 3GPP SFCGb1 (2503.5–2655 MHz).

**Steps:**
1. Read SFCG Recommendation 32-2R6 (lunar frequency allocations, June 2025).
   Also read SFCG 43-1 (June 2025): PNT band protection from surface 3GPP emissions.
   Both available at: https://sfcgonline.org/resources/recommendations/
2. Compute the guard band: 2503.5 − 2492.028 = 11.472 MHz.
3. Compute the ACS (Adjacent Channel Selectivity) requirement for NR at 2503.5 MHz:
   - 3GPP TS 38.101-1, Table 7.3.3-1 (ACS for FR1). ACS ≥ 33 dB.
4. Check whether SFCGb1 out-of-band emissions meet the SFCG 43-1 limit:
   - Maximum aggregate unwanted power in 2483.5–2500 MHz: **−121 dB(W/m²/MHz)** at PNT antenna.
   - 43-1 assumes ≥0.24 m UE-to-PNT antenna separation, ≥17 m BTS-to-PNT separation.
5. Propose the minimum guard band needed and check against SFCG allocation.

**Deliverable:** A 1-page coexistence analysis with a spectrum diagram showing AFS and SFCGb1.
This feeds into Section V of the Track S2 paper.

---

### S2-W6 — Transparent vs. regenerative ELFO payloads (Week 6)

**Goal:** Quantify the Physical Layer and SWaP implications of the two relay payload options.

**Steps:**
1. Define the two payload models:
   - **Transparent (bent-pipe):** the relay amplifies and re-transmits without demodulating.
     The PHY link spans end-to-end (surface → ELFO → Earth): Doppler and delay accumulate
     across legs, and all intelligence resides on the surface or on Earth. Lower SWaP.
   - **Regenerative (lightweight):** the relay demodulates, decodes, and re-modulates; it can
     optionally host a BPv7 node for onboard store-and-forward. Each hop terminates its own
     PHY, so Doppler is corrected per hop. Higher SWaP (OBC + storage).
2. For each payload type, recompute the S2-W4 PHY table:
   - Transparent: combined Doppler across both legs; total one-way delay 58 ms + 1280 ms.
   - Regenerative: per-hop Doppler (≈2.3 kHz during contact window) and per-hop delay budget;
     HARQ can terminate at the relay instead of on Earth.
3. Estimate the SWaP delta of the regenerative option:
   - Onboard storage requirement: use the peak-buffer metric from Student 3's DSNS runs
     (S3-W5) as the sizing driver.
   - Processing and power: document qualitatively from published smallsat OBC figures, citing
     sources (do not invent numbers).
4. Build the comparison table: payload type × {Doppler handling, timing, HARQ feasibility,
   onboard storage, SWaP, DTN support}.

**Deliverable:** Payload trade-off table — Section IV of the paper.

---

### S2-W7 — DTN integration points in the 5G stack (Week 7)

**Goal:** Evaluate the three candidate 5G–DTN convergence architectures under intermittent
ELFO connectivity.

**The three options:**
- **Option A — DTN above the UPF:** full 5G Core retained; BPv7 runs over the N6 interface.
  Maximum 5G feature preservation, but every Core transaction crosses the intermittent
  backhaul unless the Core is local.
- **Option B — DTN after the gNB:** user-plane traffic is extracted at (or just above) the
  gNB and handed to a BPv7 agent, bypassing most of the Core. Reduced SWaP and Core
  dependency, but session management and QoS must be handled outside 3GPP procedures.
- **Option C — Local lunar 5G Core + DTN backhaul:** a lightweight 5GC runs at the lander;
  DTN is used only on the trunk to Earth. Sessions terminate locally in milliseconds
  (solves the T300/T310 breakage from S2-W4); the DTN tunnel never carries 3GPP signalling.

**Steps:**
1. For each option, trace the user-plane and control-plane paths on the architecture diagram.
2. Replay a 7-day LCRNS visibility timeline (use Student 3's contact plan from S3-W3) and
   count, for each option: session-breaking events, signalling round-trips that cross the
   intermittent link, and data stalled awaiting contact.
3. Score each option on: session continuity, end-to-end latency, resilience during loss of
   Earth connectivity, CCSDS/LunaNet interoperability, and SWaP footprint on surface assets.
4. Build the 3×5 trade-off matrix (integration point × metric).

**Deliverable:** Integration trade-off matrix + recommended architecture with justification.
This is Table I of the paper.

---

### S2-W8 — End-to-end analysis with S1 coverage output (Week 8)

**Collaboration with S1.** Use the coverage GeoTIFFs produced by Student 1 to add
the surface→relay dimension to your analysis.

**Steps:**
1. From S1's LOS mask, extract which fraction of the south-pole area has LOS to ELFO relay
   during the contact window (elevation ≥ 5°).
2. Compute end-to-end link budget: surface BTS → relay → Earth DSN.
   Parameters: BTS EIRP = 53 dBm, relay gain per LCRNS SRD (esc.gsfc.nasa.gov/projects/LCRNS — Table 2 of NTRS 20250002698 contains state vectors only, not link budgets).
3. Map: for each surface pixel in LOS of relay, what is the received SNR at the DSN?
4. Combine with S2-W7: for the recommended architecture, report end-to-end latency
   distribution (surface → Earth) under the 7-day intermittency profile.

---

### S2-W9–10 — Paper draft (Weeks 9–10)

**Survey chapter to write:** `docs/survey/05-3gpp-on-the-moon.md`

**Paper title (working):** "Assessment of 5G Integration with DTN/CCSDS Using ELFO Relay
Satellites for Lunar Surface Communications"

**Paper structure:**
1. Introduction — terrestrial 5G assumptions (continuous connectivity, low latency) vs.
   lunar constraints (intermittent ELFO backhaul, SWaP, spectrum).
2. ELFO geometry — Doppler and delay time series, comparison with TR 38.821 LEO-600.
3. PHY layer — SCS selection, HARQ/timer breakage, frequency coexistence (LunaNet AFS
   vs. SFCGb1), transparent vs. regenerative payload implications.
4. 5G–DTN integration — the three DTN placement options, session continuity under the
   7-day intermittency replay, trade-off matrix.
5. System-level trade-offs — latency, resilience, complexity, SWaP.
6. Conclusions — recommended architecture and required 5G stack modifications for
   LunaNet/LCRNS compatibility.

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
   NASA NTRS: https://ntrs.nasa.gov/citations/20230012811

6. **Why this is a gap** — Search GitHub for "LCRNS contact plan" and "Moonlight contact plan."
   You will find nothing. This is the contribution.

7. **Improved CGR** — De Jonckère & Fraire (2024), arXiv:2410.15546.
   Introduces contact-splitting and edge-pruning for capacity/buffer-aware CGR (FEAP-CB).
   Read before S3-W4: the ISL capacity constraint directly motivates these techniques.
   https://arxiv.org/abs/2410.15546

8. **Lunar DTN MARL** — Vitale, Fraire et al. (2025), arXiv:2510.20436.
   Decentralized GAT-MARL routing for lunar rover DTN — useful as a baseline comparison
   when reporting the ISL study results (S3-W6). https://arxiv.org/abs/2510.20436

9. **LCRNS system overview** — Esper et al. (2025), NTRS 20250003321, SpaceOps 2025.
   Essential context on why LCRNS was designed without ISLs and what the commercial
   payload strategy is. https://ntrs.nasa.gov/citations/20250003321

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
- `lunarcomms/orbits/elfo.py` — `keplerian_state()`, `propagate_elfo()`, `south_pole_elevation_deg()`, `contact_windows()`
- `lunarcomms/geometry/frames.py` — `earth_elevation_angle_deg()`

**You own the ELFO propagator** (issues #6–7): implement `keplerian_state()` (Keplerian →
Cartesian, Bate et al. 1971 Section 2.4), `propagate_elfo()` (Kepler's equation via
Newton-Raphson, ≤ 10 iterations), and `south_pole_elevation_deg()`. Validate with
`pytest tests/test_geometry.py::TestELFOGeometry` and against NTRS 20250002698 Table 1
(period ≈ 30 h, ~15–20 h contact windows above 5°).
**Deliver to Student 2** the Doppler/delay time series and the contact window table —
their protocol analysis (S2-W3/W4) consumes these outputs.

**Steps:**
1. Propagate the 5-satellite LCRNS Reference Constellation 3.1 (elements from `data/orbits/lcrns_ref_constellation.json`)
   over 7 days (one week).
2. Compute elevation from south pole for each satellite at each time step.
3. Use `contact_windows()` to extract contact windows (min elevation = 5°).
4. Compute: how often is at least one satellite visible? (Target: ≥ 95% coverage of lunar south pole per LCRNS mission requirements, esc.gsfc.nasa.gov/projects/LCRNS.)
5. Also compute: how long is the Earth direct-to-surface link available?
   (Use `earth_elevation_angle_deg()` — Earth must be above 5° elevation AND terrain-unobstructed.)

**Acceptance criteria:**
- A 7-day contact window table (CSV): start, end, satellite, duration.
- 5-sat coverage fraction ≥ 95% at south pole (validate against LCRNS mission requirements).

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

**Deliverable:** `data/orbits/lcrns_5sat_7day_contact_plan.csv` — a ready-to-use file
for any DTN researcher studying lunar scenarios. Commit this file to the repo.

---

### S3-W5 — Router benchmark: ION-CGR vs VolCgr vs epidemic (Week 5)

**Note:** SABR is the CCSDS standard that *specifies* CGR — they are not two separate routers.
  The meaningful comparison is between *CGR variants* (ION-CGR, VolCgr from A-SABR) and baseline epidemic.
  See De Jonckère et al. (2025, IEEE WiSEE) for the VolCgr definition and benchmark methodology.
  Also see De Jonckère & Fraire (2024, arXiv:2410.15546) for the FEAP-CB capacity/buffer-aware variant
  — relevant if ISL contacts are capacity-constrained.

**Steps:**
1. Using the LCRNS 7-day contact plan, define three traffic profiles:
   - **Rover telemetry** (steady): 10 kbps constant, bundle size 1 MB, TTL 48 h.
   - **EVA video** (bursty): 1 Mbps for 30 min during EVA, then silent, bundle 100 MB, TTL 2 h.
   - **Emergency science** (low-priority): 100 kbps, preemptable by EVA traffic, TTL 7 days.

2. Run each router (ION-CGR, VolCgr, epidemic) over each traffic profile using DSNS.
   - Enable and disable custody transfer to see the effect.

3. Collect metrics:
   - Bundle Delivery Ratio (BDR)
   - 95th percentile end-to-end delay
   - Peak buffer usage at relay (bytes)
   - Number of retransmissions

4. Build the comparison table. This is Table I of your paper.

**Acceptance criteria:** A 3×3 table (3 routers × 3 traffic profiles) with all 4 metrics filled.

---

### S3-W6 — Stretch: Inter-satellite links for LCRNS (Week 6)

**Goal:** LCRNS Reference Constellation 3.1 has no inter-satellite links (ISLs). Quantify
what ISLs would add. No public ISL study exists for LCRNS as of June 2026 — this is a
novel, publishable extension.

**Steps:**
1. Extend `export_contact_plan()` with an `--isl` option: compute satellite-to-satellite
   line-of-sight (occultation test against the 1737.4 km lunar sphere) and append ISL
   contacts to the plan.
2. Characterize the ISL topology over 7 days:
   - Fraction of time each satellite pair has LOS. (Expect near-continuous: both satellites
     spend most of the orbit near apolune at ~17,400 km, so the Moon rarely blocks the path —
     unlike LEO constellations where ISLs churn constantly. Verify this claim numerically.)
   - ISL range distribution (drives the link budget).
   - Occultation events: frequency and duration.
3. Re-run the S3-W5 router benchmark on two contact plans: baseline vs. baseline+ISL.
   - Key question: how often does a satellite have surface contact but no Earth contact?
     Those intervals are exactly when ISLs pay off. Quantify the BDR and p95-delay change.
4. Capacity sweep: parametrize ISL `rate_bps` at 100 Mbps (Ka-band), 1–10 Gbps (optical,
   operational on Starlink/EDRS), and 10–100 Gbps (THz, citing theoretical link budgets only).
   Find the knee where the bottleneck shifts from link rate to contact windows or buffers.
5. Report relay buffer dimensioning with and without ISLs (peak-buffer metric from DSNS).
   Hand this number to Student 2 for the regenerative-payload SWaP analysis (S2-W6).

**Deliverable:** ISL contact plan (committed CSV) + with/without comparison table.
This becomes a novel section of the Track S3 paper.

**Alternative stretch (if time permits):** Solar System Internet — add a Mars relay node
(Earth-Mars OWLT 3–22 min, DSN window ~8 h/day, Earth-Mars distance via `pip install hapsira`)
and re-run CGR to find where it fails (storage overflow, routing-horizon loops). Document
the failure mode as an open research problem.

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
3. Router benchmark — ION-CGR vs VolCgr (A-SABR) vs epidemic on three traffic profiles.
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
| 5 | Implement `load_dem()` + `extract_profile()` + `sample_loss_tangent_params()` | S1 | W2–7 |
| 6 | Implement `keplerian_state()` + Kepler equation solver | S3 | W3 |
| 7 | Implement `propagate_elfo()` + `south_pole_elevation_deg()` | S3 | W3 |
| 8 | Implement `load_lcrns_elements()` + `coverage_fraction()` | S3 | W4 |
| 9 | NR/NTN procedure inventory + Rel-17 lunar readiness table (PHY + MAC + RRC), with required modifications and justification | S2 | W3–5 |
| 10 | Implement `contact_windows()` + `export_contact_plan()` | S3 | W4 |
| 11 | Run CGR/SABR/epidemic benchmark on LCRNS contact plan | S3 | W5 |
| 12 | Write survey chapter `03-rf-propagation.md` | S1 | W9 |
| 13 | Write survey chapter `05-3gpp-on-the-moon.md` | S2 | W9 |
| 14 | Write survey chapter `06-dtn-and-solar-system-internet.md` | S3 | W9 |
| 15 | Monte Carlo uncertainty on coverage maps | S1 | W7–8 |
| 16 | Solar System Internet stretch (Mars relay) | S3 | W6 |
| 17 | End-to-end integration notebook | All | W10 |
| 18 | Add `references.bib` entries for all cited papers | All | ongoing |

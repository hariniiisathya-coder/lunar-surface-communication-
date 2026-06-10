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
The contribution is an exhaustive analysis of how a SWaP-constrained private 5G network at a
lunar moonbase can interoperate with CCSDS/Bundle Protocol v7 over an intermittent ELFO relay,
including protocol-level analysis of blackout management, reconnection procedures, and
energy-aware operation. Student 2 does not write simulation code; geometry inputs come from S3.

**Central constraint: SWaP.**
The lander/moonbase has strict Size, Weight and Power limits. Every protocol choice
(5GC function set, DTN placement, QoS policy, buffer sizing, power cycling) must be
justified against SWaP. The research question is not "can 5G work?" but
"what is the minimum viable 5G stack that is CCSDS-interoperable and energy-aware?"

**Survey chapters:** `docs/survey/02-relay-architectures.md`, `docs/survey/05-3gpp-on-the-moon.md`

**Research questions:**
1. Does the 5G NR link budget close from ELFO altitude (17,400 km) with realistic
   satellite SWaP? This determines whether Architecture B (satellite gNB) is viable
   at all, or whether Architecture A (surface-only 5G + CCSDS relay) is the only option.
2. How does the 5G stack behave during ELFO blackouts (gap periods with no Earth link)
   and during reconnection (contact window start) — layer by layer at the lander?
3. What explicit adaptation layer is required to connect 5G’s IP-centric N6 interface
   to CCSDS/BPv7, and what 3GPP assumptions does it violate?
4. How should energy and bandwidth be prioritised during a contact window
   (emergency data vs telemetry vs state sync vs config updates)?

**Primary architectural fork: transparent vs. regenerative ELFO payload.**
This choice determines what role the ELFO can play in the 5G system and therefore
what coverage area is achievable at the south pole:

```
┌────────────────────────────────────────────────────────┐
│ Architecture A — Transparent ELFO (bent-pipe)             │
│                                                           │
│ Rover/EVA ←5G NR surface→ Lander (gNB+5GC+DTN gateway)   │
│                              │ CCSDS/LunaNet (bent-pipe) │
│                             ELFO                          │
│                              │ amplified RF to Earth DSN │
│ Coverage: surface only (~1–10 km from lander, terrain)    │
│ 5G role: surface access only; ELFO is CCSDS relay         │
│ 5GC: local at lander; N6→IP→DTN gateway adaptation needed │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Architecture B — Regenerative ELFO (satellite gNB/IAB)   │
│                                                           │
│ Rover/EVA ←5G NR surface→ Lander (gNB+5GC)               │
│ Rover/EVA ←5G NR from orbit→ ELFO (satellite gNB, NTN)   │
│                              │ F1/N3 over CCSDS backhaul │
│                             Lander 5GC                    │
│                              │ DTN trunk to Earth DSN    │
│ Coverage: wide-area south pole from apolune 17,400 km     │
│ 5G role: NTN satellite gNB (3GPP IAB or NTN architecture)  │
│ Key issue: F1/N3 over intermittent CCSDS link to local 5GC │
└────────────────────────────────────────────────────────┘
```

**Critical points:**
1. 5G is designed to connect UEs to an IP data network (N6 interface). It has no native
   DTN/store-and-forward capability. Any DTN integration requires an explicit adaptation
   layer (N6 → IP → DTN gateway, or F1/N3 over CCSDS).
2. The correct 3GPP framework for this network is a **Standalone Non-Public Network
   (SNPN)** per TS 23.501 Section 4.11: a self-contained 5G network with its own PLMN
   ID, no roaming, no connection to a public operator. The SNPN can optionally sync with
   Earth-side operations during contact windows but is fully autonomous otherwise.
3. The 5G stack requires concrete modifications that do not exist in the current specs:
   extended eDRX, SNPN-specific OAM, UPF buffer policy for DTN drain, AMF/SMF state
   persistence across power cycles, and a gNB minimal-beacon power mode. Enumerating
   and justifying these modifications is the main contribution of Track S2.

**Final deliverable:** Architecture comparison (transparent vs. regenerative) ×
{coverage area, SWaP, 3GPP modifications needed, CCSDS integration point, blackout
management, spectrum compliance}, with recommendation and justification.

---

### S2-W1 — Background reading (Week 1)

1. **5G architecture** — 3GPP TS 38.300 v17.x, Section 4 (NR architecture overview).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.300/

2. **NTN fundamentals** — 3GPP TR 38.811 v15.4, Sections 5–6 (NTN channel model, LEO/GEO).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.811/
   *(Arch B only: only relevant if S2-W2 link budget shows satellite gNB is feasible.)*

3. **NTN system design** — 3GPP TR 38.821 v16.x, Section 6 (solutions for NR NTN).
   Specifically: Section 6.2 (timing), 6.3 (HARQ), 6.4 (PRACH).
   Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.821/
   *(Arch B only: CU/DU split and F1-AP over high-delay links. Skip if Arch B is not viable.)*

4. **Lunar 5G baseline** — Edwards et al. (2023), NTRS 20220015268
   ("3GPP Telecommunications Technology on the Moon"). Read Sections III-IV (link budget and coverage).

5. **Updated 5G lunar study** — Wagner et al. (2025), NTRS 20250001947
   ("Envisioned Lunar Surface Comms Using 3GPP Cellular and Wi-Fi Technologies").
   Companion to Edwards 2023; covers Artemis V multi-rover scenario, SWaP, Nokia/Axiom spacesuit
   integration. Read alongside item 4 — this is the most current NASA Glenn assessment.

6. **LunaNet AFS** — LunaNet Interoperability Specification v5, Section 3.2.
   (AFS frequency 2492.028 MHz and its proximity to 3GPP SFCGb1 band.)
   NASA NTRS: https://ntrs.nasa.gov/citations/20230012811

7. **DTN fundamentals** — CCSDS 734.2-B-2 (Bundle Protocol v7), Sections 1–3.
   Free download: https://public.ccsds.org/Pubs/734x2b2.pdf
   (Coordinate with Student 3 — this is their core spec. You need it to reason about
   where BPv7 attaches to the 5G stack.)

8. **5G system architecture** — 3GPP TS 23.501 v17.x, Sections 4.2 and **4.11**.
   Free download: https://www.3gpp.org/ftp/Specs/archive/23_series/23.501/
   Section 4.2: user-plane path (UE → gNB → UPF → N6) and control-plane NFs.
   **Section 4.11: Non-Public Networks (NPN) — specifically Standalone NPN (SNPN).**
   This is the 3GPP framework that formally describes the lunar private network.
   Understand SNPN PLMN ID format, UE access control, and SNPN-specific NAS procedures.

9. **LCRNS system overview** — Esper et al. (2025), NTRS 20250003321, SpaceOps 2025 paper #257.
   System-level LCRNS context: commercial payload strategy, constellation coverage, and
   bent-pipe vs. regenerative trade-offs from the programme office perspective.
   https://ntrs.nasa.gov/citations/20250003321

10. **3GPP Rel-19 NTN** — 3GPP Release 19 (completed Dec 2025).
    NR_NTN_Ph3 work item on regenerative vs. transparent payload architecture for GEO/NGSO.
    https://www.3gpp.org/specifications-technologies/releases/release-19

11. **µD3TN DTN stack** — Wischer et al. (2024), arXiv:2407.17166.
    Modular BPv7 software stack with CCSDS SPP convergence layer. Relevant for
    understanding how to implement the CL adapter between gNB/UPF and the DTN node.
    Open-source: https://gitlab.com/d3tn/ud3tn

12. **5G power saving** — 3GPP TS 38.331 v17.x, Section 5.7 (RRC power saving);
    3GPP TS 24.501 v17.x, Section 5.3.7 (NAS eDRX).
    Understand DRX, eDRX, and RRC_IDLE/INACTIVE states. In the lunar scenario, eDRX
    cycles may need to be orders of magnitude longer than terrestrial values.
    Free download: https://www.3gpp.org/ftp/Specs/archive/38_series/38.331/

---

### S2-W2 — SWaP analysis: RAN dominates, Core is trivial (Week 2)

**Goal:** Establish where SWaP actually matters in a lunar 5G deployment. The key finding
of this week is that **the 5GC is SWaP-trivial for a small private network** — the dominant
SWaP consumers are the RAN components (surface gNB and, critically, the satellite gNB in
Architecture B). This frames the rest of the study correctly.

**Steps:**

**Part A — 5GC SWaP (establish that it is not the bottleneck):**
1. A private lunar 5G network has ~10–20 UEs (rovers + EVA suits). Modern open-source
   5GC implementations (Open5GS, free5GC) run AMF+SMF+UPF on ARM Cortex-A class hardware
   at ~5 W. Document this with reference to published figures.
2. Map 3GPP NFs (TS 23.501 Section 4.2) to their necessity for an isolated private network:
   - **Essential:** AMF, SMF, UPF. Run locally, no Earth contact needed during gap.
   - **Simplifiable:** UDM (static subscriber table), AUSF (pre-provisioned credentials).
   - **Eliminable:** PCF (static QoS rules), NRF, CHF, NEF, NSSF.
   - **Conclusion:** minimum viable 5GC ~5–15 W, ~0.5 kg — not the architectural constraint.
3. Compute UPF buffer sizing (the one non-trivial Core requirement):
   - Worst-case gap duration (from S3-W3) × aggregate surface traffic
     (10 kbps telemetry + 1 Mbps EVA burst, from S3-W5 profiles).
   - This is storage, not compute. Hand to S3-W5 and S2-W6.

**Part B — RAN SWaP (the real constraint):**
4. **Surface gNB at lander** — estimate the power budget for the RF front-end:
   - Target coverage: ~5 km radius on lunar terrain at SFCGb1 (2.5 GHz).
   - Required EIRP: use Edwards 2023 (NTRS 20220015268) Table IV link parameters as
     baseline (S1 terrain-aware outputs will refine this in W6 when available).
   - Estimate BTS transmit power, antenna gain, PA efficiency, baseband compute.
   - Document the PA + antenna + baseband SWaP breakdown.
   - This is where the lander power budget is consumed — not the Core.

5. **Satellite gNB on ELFO (Architecture B only) — link budget feasibility check:**
   This is the critical SWaP question for Architecture B. Can you close a 5G NR link
   from 17,400 km with realistic satellite hardware?
   - Path loss at 2.5 GHz, 17,400 km: L = 20·log10(4π·17400e3/0.12) ≈ **191 dB**.
   - Compare: LEO-600 km path loss ≈ 164 dB. ELFO adds ~27 dB vs. LEO.
   - 3GPP TS 38.101-1 minimum UE sensitivity (PUSCH): ~ −95 dBm (15 kHz SCS, 1 RB).
   - For rover UE to close the uplink: required satellite receive sensitivity = UE EIRP
     − path loss. With UE EIRP ~23 dBm (handheld), received power ≈ 23 − 191 = −168 dBm.
     Required satellite G/T must compensate ~73 dB gap vs. LEO reference.
   - **Preliminary finding:** closing the NR link from ELFO altitude requires either a
     very high-gain satellite antenna (large aperture, high SWaP on satellite) or
     high-gain rover antenna (directional, SWaP on UE side). Document quantitatively.
   - Cite Esper 2025 (NTRS 20250003321) for LCRNS payload SWaP context; Wagner 2025
     (NTRS 20250001947) for surface terminal SWaP figures.

**Deliverable:** Two-part SWaP summary:
(1) 5GC is not the bottleneck — minimum viable Core ~5–15 W, standard embedded hardware.
(2) RAN SWaP analysis: surface gNB power budget + Architecture B link budget feasibility.
**If the Architecture B link budget cannot close with realistic satellite SWaP, this is a
key finding that eliminates or severely constrains Arch B — document with numbers.**

---

### S2-W3 — 3GPP interface analysis at the lander integration point (Week 3)

**Goal:** Identify exactly which 3GPP interfaces and procedures are at the boundary
between 5G and CCSDS/DTN at the lander, and what each architecture requires from them.

**Key clarification on scope:**
- The 5G NR surface link (rover ↔ lander gNB) has microsecond delays and negligible
  Doppler. **No NR access procedure needs modification** — standard NR works as-is.
- The ELFO geometry (Doppler, delay) is irrelevant to the surface NR link.
- The integration challenge is at the **lander node**, where 5G terminates and CCSDS begins.
- For Architecture B: NTN analysis of the ELFO satellite gNB is **conditional** on the
  S2-W2 link budget result. If the link budget does not close, Arch B is not viable and
  this analysis reduces to Arch A only.

**Steps:**

**Part A — SNPN configuration: the 3GPP framework for the lunar private network**
1. Read TS 23.501 Section 4.11 (Non-Public Networks). Identify which SNPN-specific
   procedures differ from a public PLMN deployment:
   - PLMN ID assignment for the lunar network (no ITU-assigned MCC/MNC; propose a
     private-use range and document the implications for UE provisioning).
   - UE access control: only pre-provisioned rovers/suits may attach (no open access).
   - NAS: no Home Network involvement; AUSF/UDM run entirely locally.
   - OAM (O1/O2 interface): in connected mode, OAM data streams to Earth operations
     centre; in isolated mode, alarms and KPIs are logged locally for later upload.
2. Define the two OAM modes for the SNPN:
   - **Connected mode** (ELFO in view): O1/O2 telemetry streamed to Earth ops via DTN;
     remote configuration commands received from Earth (within contact window).
   - **Isolated mode** (ELFO gap): local OAM only; alarms queued for DTN delivery;
     no remote commands possible; pre-loaded automation scripts govern the network.
3. Document which SNPN NAS procedures require modification for the lunar scenario and
   which work as-is. Cite TS 23.501 Section 4.11 and TS 24.501 Section 4.5 (SNPN NAS).

**Part B — Data lifecycle: from rover collection to Earth delivery**
4. Trace the complete data path for a science data collection campaign:
   - Rover sensor data → 5G UE PDU session → gNB → UPF (N6) → DTN gateway.
   - DTN gateway: data categorised by type (science/telemetry/EVA video/housekeeping)
     and mapped to bundle priority (cite `ccsds_sabr` for scheduling).
   - During ELFO gap: bundles queued locally at the DTN agent.
   - Contact window opens: bundles drained to ELFO by priority; large science datasets
     may span multiple contact windows (bundle fragmentation / custody transfer).
   - Earth DSN: bundles reassembled, delivered to mission operations centre.
5. Identify where data can be lost (TTL expiry, buffer overflow) and what the
   protocol must do: which data types are expendable (real-time video) vs. must be
   delivered with custody (science observations, safety logs)?

**Part C — Architecture A: N6 interface as the 5G/CCSDS boundary**
6. Read TS 23.501 Section 5.6 (N6 interface). Identify every assumption it makes
   about the DN that breaks for a DTN gateway:
   - DN always reachable; DN is IP-based; QoS enforcement ends at N6.
7. For each broken assumption, document what the DTN gateway must provide and what
   3GPP hooks exist (PFCP/N4 between SMF and UPF, TS 29.244).

**Part D — Architecture B (conditional on S2-W2 link budget): F1-AP over CCSDS**
8. Read 3GPP TS 38.473 (F1-AP). Classify each procedure by latency budget:
   - Latency-sensitive (cannot tolerate ~58 ms OWLT): UE Context Setup/Modification,
     DL/UL RRC message transfer, scheduling-related signalling.
   - Tolerable: F1 Setup (once-only), gNB-DU Configuration Update (periodic).
   Build table: procedure | latency budget | CCSDS-compatible? | modification needed.
   Only execute if Arch B link budget closed in S2-W2.

**Deliverable:** Three tables:
- SNPN configuration delta vs. public PLMN (Part A).
- Data lifecycle diagram + custody/TTL policy per data type (Part B).
- N6 assumptions broken + gateway API requirements (Part C).
- F1-AP compatibility table (Part D, Arch B only if viable).
All feed into S2-W4 (power states + blackout) and S2-W7 (DTN gateway spec).

---

### S2-W4 — Blackout and reconnection protocol analysis (Week 4)

**Goal:** Analyse exhaustively what happens in the 5G stack — layer by layer — when the
ELFO link goes dark (blackout onset) and when it comes back (contact window start).
This is the core protocol contribution of Track S2.

**Note on the surface 5G link:** Rover ↔ lander delay is microseconds, Doppler is
negligible. Standard NR parameters work without modification on the surface segment.
The protocol challenge is entirely at the lander's interface between the local 5GC
and the CCSDS/DTN backhaul.

**Steps:**

**Part A — Blackout onset (ELFO goes below horizon):**
1. **User plane (UPF):** When the DTN gateway signals "no contact," the UPF switches
   from "forward to DTN" to "buffer locally."
   - What triggers this transition? (DTN CL status, from S3 contact plan.)
   - Per-QoS-flow buffer policy: which flows keep buffering (telemetry, science),
     which are dropped after TTL (real-time video, emergency if gap > TTL)?
   - Cite TS 23.501 Section 5.7 (QoS framework) for flow priorities.
2. **Control plane (AMF/SMF):** PDU sessions stay active locally — rovers remain
   registered. Verify per-procedure that no Earth contact is needed:
   - Authentication (AUSF): pre-provisioned credentials — works offline.
   - Policy (PCF): cached locally — works offline.
   - Mobility (AMF): local — works offline.
   - **Finding:** surface network continues uninterrupted during gap. Document per procedure.
3. **Energy management at blackout onset:**
   - Power down: lander CCSDS modem and RF frontend toward ELFO (no contact — no
     need to transmit or listen on the relay link).
   - Keep active: surface gNB (rovers stay connected), AMF/SMF, UPF (buffering).
   - Estimate power saved by powering down the CCSDS relay hardware during gap.

**Part B — Energy save modes (sustained gap, no full power-down):**
1. **Extended eDRX for rovers (UEs):** Rovers save battery by entering eDRX.
   - Current 3GPP NTN Rel-17 max eDRX = 10,485.76 s (~2.9 h). Is this sufficient for
     the worst-case gap from S3-W3? If not: document the required spec change
     (TS 38.331 Section 6.3.2 eDRX parameters; TS 24.501 Section 5.3.7).
   - During eDRX, gNB buffers DL data and pages rover at the paging window.
     For local SNPN AMF, paging is fully local — no Earth contact needed.
   - **Proposed modification:** eDRX cycle configurable up to worst-case gap duration.
2. **gNB minimal-beacon mode:** With no active sessions, reduce gNB to SSB/SIB-only
   broadcast; power down PDSCH/PUSCH amplifiers and UL receiver.
   - Not a standard 3GPP mode — document as required modification; estimate power saving.

**Part C — Full power-down and resurrection (very long gap or planned maintenance):**
3. **Power-down checkpoint procedure:**
   - AMF: persist all UE contexts to non-volatile storage. Note: 3GPP TS 23.502
     defines no standard Core power-down procedure — **required modification**.
   - SMF: persist PDU session parameters. UPF: flush RAM buffers; confirm all bundles
     persisted before shutdown. gNB: persist cell config (UEs will re-attach).
4. **Resurrection sequence (power-up):**
   - Order: storage restore → Core NFs online → gNB cell bring-up (SSB/SIB broadcast)
     → rovers re-attach via RACH → PDU sessions re-established → DTN agent resumes
     → (if ELFO in view) CCSDS link opens, bundle queue drains by priority.
   - Estimate time-to-first-data per step; identify failure modes.

**Part D — Contact window reconnection (standard case, no full power-down):**
5. DTN agent opens CLAs; drains queue by SABR priority:
   emergency → science/telemetry → SNPN OAM log upload → config updates from Earth.
   Cite `ccsds_sabr`. Note: no per-rover re-authentication (AUSF pre-provisioned locally).
   Define contact-window budget: fraction for data drain vs. OAM sync.

**Deliverable:**
- Power state machine diagram: Normal → Energy-Save (eDRX) → Deep-Sleep → Resurrection,
  with transitions, triggers, and estimated power at each state.
- "5G Lunar Protocol Modification Table": one row per required stack change:
  Component | Standard behaviour | Proposed modification | Spec clause to modify.
  This table is the core contribution of Track S2 — Table II of the paper.

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

### S2-W6 — Architecture comparison: transparent vs. regenerative (Week 6)

**Goal:** This is the central analytical week of Track S2. Compare the two ELFO payload
architectures across every dimension that matters: coverage area, 5G protocol implications,
CCSDS integration point, SWaP, and spectrum. The output is the main contribution table.

**Steps:**
1. **Coverage comparison** (use S3-W3 contact windows and S1 terrain outputs):
   - Architecture A (transparent): 5G coverage = lander BTS surface footprint only
     (terrain-limited, ~1–10 km, per S1 propagation model). ELFO provides no 5G coverage
     — it only relays CCSDS traffic. Coverage predictability = ELFO visibility schedule.
   - Architecture B (regenerative, satellite gNB): 5G coverage from ELFO apolune
     (17,400 km altitude over south pole) — approximately the entire south-pole hemisphere
     visible to ELFO, during contact windows only. Estimate the 5G NR link budget
     from ELFO to surface at SFCGb1 (2503.5–2655 MHz): EIRP, path loss, required UE
     sensitivity. Compare against 3GPP TS 38.101-1 minimum sensitivity.
     Note: rovers/EVA suits need directional or high-gain antennas — document SWaP impact.

2. **5G protocol implications per architecture:**
   - Architecture A: standard 5G NR on the surface, no NTN modifications. The only
     non-standard element is the N6→IP→DTN adaptation at the lander (gateway function).
     Which 3GPP specifications govern this interface and what is needed beyond them?
   - Architecture B: ELFO acts as satellite gNB (3GPP NTN, TR 38.821). What 3GPP
     modifications are needed for an ELFO-altitude gNB (F1 over CCSDS, scheduling
     over intermittent backhaul, CU/DU split with DTN in between)?
     Key reference: 3GPP Rel-19 NTN work items (`3gpp_rel19_ntn`).

3. **CCSDS/DTN integration point per architecture:**
   - Architecture A: DTN gateway at lander N6 interface. IP PDUs → BPv7 bundles.
     Adaptation layer needed (cite µD3TN `wischer2024ud3tn` for CL adapter design).
     BPv7 carries the IP user-plane traffic as payload — 5G is unaware of DTN.
   - Architecture B: F1/N3 interface between ELFO gNB (DU) and lander 5GC (CU)
     must cross the CCSDS link. This is NOT standard — F1 is designed for low-latency
     fibre links. Document the modifications needed to run F1-AP over a DTN carrier.

4. **SWaP per architecture** (lander + ELFO satellite separately):
   - Architecture A — lander: AMF+SMF+UPF+DTN gateway (minimum viable 5GC from S2-W2)
     + CCSDS modem. ELFO: amplifiers + transponder only (low SWaP).
   - Architecture B — lander: AMF+SMF+UPF (CU side). ELFO: full gNB (DU: baseband,
     radio, OBC, storage) + CCSDS backhaul modem. Estimate using published smallsat
     OBC figures; use S3-W5 peak-buffer as onboard storage sizing driver.

5. **Build the comparison table:**
   Architecture × {coverage area, contact-window dependency, 3GPP modifications needed,
   CCSDS integration point, lander SWaP, ELFO SWaP, spectrum used, blackout behaviour}.

**Deliverable:** Architecture comparison table — the main result of Track S2.
This is Table I (or Table II if the blackout table from S2-W4 is Table I) of the paper.

---

### S2-W7 — DTN integration specification (Week 7)

**Goal:** Synthesise the S2-W6 architecture comparison with the S2-W4 blackout analysis
to derive the recommended DTN integration point for each architecture and produce the
final end-to-end protocol stack specification.

**Key framing:** 5G NR connects UEs to an IP data network (N6 interface to DN).
DTN/BPv7 is NOT an IP network. The integration requires an explicit adaptation gateway.
This week documents exactly what that gateway must do in each architecture.

**Steps:**
1. **Architecture A DTN gateway (N6 → BPv7):**
   - IP packets from UPF N6 → encapsulated as BPv7 bundle payload.
   - Gateway runs a DTN agent (cite µD3TN `wischer2024ud3tn`) with a TCPCL or CCSDS SPP
     convergence layer toward the ELFO relay.
   - During gap: gateway buffers IP packets locally (or signals UPF to buffer).
   - During contact: gateway drains buffer to ELFO using CCSDS channel; applies
     QoS-to-bundle-priority mapping (5QI → bundle priority, cite TS 23.501 Table 5.7.4-1
     and `ccsds_sabr`).
   - Draw the full protocol stack: UE PHY/MAC/RLC/PDCP/NAS → gNB → UPF N6 → DTN agent
     → CCSDS CL → ELFO → Earth DSN.

2. **Architecture B DTN gateway (F1/N3 over CCSDS):**
   - ELFO DU (gNB) communicates with lander CU (5GC) via F1-AP and GTP-U/N3.
   - These interfaces are IP-based and assume low latency. Running them over an
     intermittent CCSDS link requires:
     - F1-AP messages to be tunnelled via a CCSDS framing layer.
     - Scheduling grants to account for the ELFO-lander OWLT (~58 ms).
     - Buffer at ELFO DU for uplink data during CCSDS contact gaps.
   - Document which F1-AP procedures are latency-sensitive and which can tolerate
     the CCSDS delay. Reference TR 38.821 NTN CU/DU split analysis.

3. **Energy and bandwidth budget for the contact window (both architectures):**
   - Contact window capacity = LCRNS channel rate × window duration (from S3-W3).
   - Priority ordering for the window: emergency → science telemetry → 5GC re-sync
     → config updates. Allocate % of window to each category.
   - Document how QoS flows at the 5G level translate to bundle scheduling at the DTN level.

**Deliverable:** Full protocol stack diagrams for both architectures + DTN gateway
specification + contact-window budget table. This feeds directly into S2-W8 synthesis.

---

### S2-W8 — Architectural synthesis and LunaNet/CCSDS compatibility check (Week 8)

**Goal:** Consolidate the W3–W7 protocol analyses into a single, coherent architectural
recommendation. Verify that the recommended option is compatible with LunaNet and CCSDS
interoperability requirements. Prepare S2's contribution to the shared integration notebook.

**Note on scope:** Computing per-pixel SNR maps or terrain-aware link budgets is S1's
deliverable. S2's input to the end-to-end picture is the recommended protocol architecture
and the latency/continuity characterisation — not RF propagation.

**Steps:**
1. Synthesise the findings from S2-W3 (interface analysis), S2-W4 (blackout/reconnection),
   S2-W5 (spectrum coexistence), S2-W6 (architecture comparison table), and S2-W7 (DTN
   gateway specification) into a single architectural recommendation with written
   justification for each design choice, citing the specific spec clauses.
2. Verify LunaNet/CCSDS compatibility of the recommended architecture:
   - Does the recommended DTN placement satisfy LunaNet ICD v5 Section 4.1 (BPv7 required)?
   - Are the proposed 3GPP modifications within the scope of 3GPP Rel-19 NTN work items,
     or do they require a new study item? Cite `3gpp_rel19_ntn`.
   - Does the surface-to-relay frequency plan comply with SFCG 32-2R6 and SFCG 43-1
     (from S2-W5)? Confirm guard band and out-of-band limits are met.
3. Using S3's 7-day contact plan (S3-W4 output), compute the end-to-end latency
   distribution (surface → Earth) under the recommended architecture:
   - For the viable architecture(s) from S2-W6 (Arch A always; Arch B only if link
     budget closed in S2-W2): sessions broken per day, median and p95 data-delivery
     latency, fraction of contact time lost to protocol overhead.
   - This is the quantitative evidence for the main comparison table.
4. Prepare a 2-page summary document: "S2 contribution to integration notebook"
   describing which architecture (A or B) to instantiate in
   `notebooks/07-first-link-budget.ipynb` and what protocol parameters to configure
   (DTN gateway type, bundle priority policy, contact-window budget allocation).

---

### S2-W9–10 — Paper draft (Weeks 9–10)

**Survey chapter to write:** `docs/survey/05-3gpp-on-the-moon.md`

**Paper title (working):** "Assessment of 5G Integration with DTN/CCSDS Using ELFO Relay
Satellites for Lunar Surface Communications"

**Paper structure:**
1. Introduction — why 5G at the lunar south pole; ELFO as coverage/backhaul enabler;
   SWaP constraints; 5G’s IP-centric and always-connected design vs. lunar reality.
2. System model — SNPN configuration; ELFO contact windows and gap model (from S3);
   data lifecycle from rover collection to Earth delivery.
3. Architecture A: transparent ELFO + surface 5G SNPN + N6→DTN gateway — protocol
   stack, DTN adaptation layer, power state machine, spectrum coexistence.
4. Architecture B (if viable per S2-W2 link budget): regenerative ELFO as satellite
   gNB — F1/N3 over CCSDS, coverage extension, SWaP cost.
5. Required 5G stack modifications — explicit table: eDRX extension, SNPN OAM,
   UPF buffer policy for DTN, AMF/SMF state persistence, gNB beacon mode,
   N6 DN availability signalling. For each: spec clause, required change, justification.
6. Comparison and recommendation — coverage, SWaP, 3GPP compliance, CCSDS integration.
7. Conclusions — recommended architecture; open 3GPP standardisation gaps.

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
the LCRNS/Moonlight constellation as of June 2026.

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
S3 ELFO contact windows (from S3-W3) + contact plan (from S3-W4)
   → relay_visible[t] = elevation_deg > 5
   → bundle_delivered = CGR(contact_plan, traffic)
S2 Recommended architecture (from S2-W7)
   → integration_option = {A | B | C}  [determines protocol stack used in demo]
```

**Joint deliverable:**
A single Jupyter notebook `notebooks/07-first-link-budget.ipynb` that:
1. Loads S1's S-band coverage GeoTIFF.
2. Overlays S3's ELFO contact windows (relay_visible[t] from S3-W3 output).
3. Runs one bundle delivery simulation in DSNS using S3's contact plan (from S3-W4).
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

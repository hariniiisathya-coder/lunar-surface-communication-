# Chapter 0 — Scope, Scenario, and Survey Structure

## Purpose

This document is the living survey component of `lunar-comms-survey`. It accompanies
the Python codebase in `lunarcomms/` and is structured so that every identified
gap in the literature maps directly to a module in the package.

The survey spans eight chapters:

| Chapter | Topic | Code module |
|---------|-------|------------|
| 00 | Scope and scenario | (this file) |
| 01 | Geometry and coordinate frames | `lunarcomms.geometry.frames` |
| 02 | Relay architectures: ELFO, LCRNS, Moonlight, Queqiao | `lunarcomms.orbits` |
| 03 | RF propagation models | `lunarcomms.propagation` |
| 04 | Regolith dielectrics | `lunarcomms.regolith` |
| 05 | 3GPP/5G on the Moon | (analysis module) |
| 06 | DTN and the Solar System Internet | `lunarcomms.orbits.lcrns` |
| 07 | Tooling and gaps | (cross-cutting) |
| 08 | Open problems | (future work) |

---

## The shared scenario

All three tracks of this project are grounded in the same physical scenario:

```
  ┌─────────┐
  │   DSN   │  Earth — one-way light time 1.18–1.36 s
  └────┬────┘
       │ X-band trunk (8.4 GHz downlink)
  ┌────┴─────────┐
  │   LCRNS-1   │  ELFO: a=5500 km, e=0.60, i=57.7°, ω=90°
  │  / Moonlight│  Period ~10 h; ~7–8 h visible per orbit from south pole
  └────┬─────────┘
       │ S-band 2.5 GHz (SFCGb1: 2503.5–2655 MHz)
  ┌────┴────┐
  │  BTS    │  Connecting Ridge crest (~89.5°S, 222°E, ~3 200 m above floor)
  │ h = 30 m│  Artemis III candidate landing region
  └────┬────┘
       │ 5G NR surface (S-band / UHF)
  ┌────┴────┐
  │Rover/EVA│  1–10 km radius, antenna h = 2 m, south-pole terrain
  └─────────┘
```

**Why this scenario?**

1. **Connecting Ridge** is the highest continuously illuminated point closest to the
   Shackleton crater rim in the NASA Artemis III candidate landing regions
   [@nasa2022artemis_regions]. It provides the best line-of-sight to both
   the surrounding terrain and to relay satellites.

2. **LCRNS-1 / Moonlight** are the first operational relay satellites with
   published orbital parameters that place the apoapsis over the south pole
   during the contact window [@lcrns_ref_const_31; @lunar_pathfinder_esa].

3. **S-band** is the only frequency band simultaneously allocated for lunar
   surface proximity links (SFCG 32-2R5, SFCGb1) and compatible with
   3GPP NR commercial chipsets [@sfcg32_2r5; @edwards2023].

---

## Survey template (per chapter)

Each subsequent chapter follows this structure:

### 1. What the literature does
Summary of published methods, models, and datasets used. Tables of assumptions
where relevant.

### 2. Silent assumptions
Parameters taken as given without measurement support, or extrapolated beyond
their validation range. These are the methodological vulnerabilities that a
reviewer would challenge.

### 3. Measurement support vs. extrapolation
For each key quantity: is it measured, modelled, or assumed? At what
resolution/frequency/location? What is the stated uncertainty?

### 4. The gap
A single sentence identifying the primary methodological gap.

### 5. This repo's response
The module, function, or dataset added by this project to address the gap.
If not yet addressed: `TODO — see TASKS.md issue #N`.

---

## Reading order for new students

**Week 0 — before looking at any code:**

1. NASA Moon Fact Sheet: https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
2. Wikipedia "Orbit of the Moon" (orbital parameters, synodic period, libration)
3. LROC QuickMap: https://quickmap.lroc.asu.edu/ — spend 1 h exploring the south pole.
4. Edwards et al. (2023) [@edwards2023] — the main baseline you are improving on.
5. LunaNet ICD v5 [@lunanet_icd_v5] — Sections 1 and 3.2 only.

**Chapters 01–04 correspond to Track S1.**
**Chapters 02, 05 correspond to Track S2.**
**Chapters 02, 06 correspond to Track S3.**

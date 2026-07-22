# MATLAB demo — lunar surface tap model → 5G NR link level

Closes the loop from the coverage pipeline to a 5G link-level simulation:
the two-ray + Deygout taps become a `nrTDLChannel` (`DelayProfile='Custom'`)
that an NR waveform can be pushed through.

## Files
- `site04_traj_S.mat` — a 1.79 km rover traverse across the Site04 LOLA/PGDA
  tile (179 waypoints), taps from `lunarcomms.export.taps`. Regenerate with
  `python analysis/export_taps_demo.py` from the repo root.
- `run_nrtdl_demo.m` — loads the `.mat`, plots the fading / SNR / spectral-
  efficiency trace (`site04_traj_S_trace.png`), and — if the 5G Toolbox is
  installed — replays representative waypoints through `nrTDLChannel` and
  cross-checks the measured channel gain against the deterministic tap
  prediction.

## Run
```matlab
cd matlab
run_nrtdl_demo
```

Sections 1–2 are toolbox-free. Section 3 needs the 5G Toolbox; it is skipped
with a message otherwise.

## Why this matters
The lunar surface channel is **sparse** — the two-ray excess delay is
sub-nanosecond at 30 m / 2 m mast geometry, so both rays collapse into one
complex tap and links carry 1–3 taps total. `nrTDLChannel`'s Custom profile
represents that exactly (no truncation, unlike terrestrial delay spreads),
and the along-track trace turns the two-ray spatial nulls into the time
fading a moving UE experiences. Swap the probe signal for
`nrWaveformGenerator` + `nrPUSCHDecode` to get per-band BLER/throughput
curves over real terrain — the planning-tool → link-level bridge.

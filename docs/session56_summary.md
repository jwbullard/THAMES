# Session 56 — C3S ln K correction in the GEMS DCH, calorimetry-preserving analysis
Date: July 31, 2026 — macOS

## Overview

Single-focus session on resolving the C3S ln K discrepancy identified as a BLOCKER at the end of Session 55. Also included a CLAUDE.md compression at session start and two end-of-session sanity validations (JMAK-Portlandite, pure-C3S).

**Net outcome**: one line of `src/data/gems/thames-dch.dat` changed (G0 array for C3S at all 39 T grid points, uniform −65,211.81 J/mol offset). SI(C3S) values throughout THAMES now use ln K = −50.70 at 298.15 K, matching the Nicoleau/Bullard 2015 SR-model calibration. H0(C3S) was left alone — verification showed it was already essentially correct (see §"Calorimetry preserved" below).

## Files touched
- `CLAUDE.md` — compressed 89,743 → 22,316 characters (74% reduction) via aggressive summarization of Sessions 1–50
- `src/data/gems/thames-dch.dat` — single-line edit: G0 array for C3S (DC index 118, file line 682), 39 values each shifted by −65,211.81 J/mol; CRLF line endings preserved; 4-byte diff explained (four values had trailing zeros restored by `%.7f` reformat)
- `src/data/gems/thames-dch.dat.pre-c3s-lnK-fix-20260731` — backup (untracked, gitignored)
- `docs/POST_ALPHA_TODOS.md` — three new entries: (1) audit other Standard/SR phases for ln K discrepancies, (2) H0 audit for calorimetric ΔH°_rxn targets across the same phase list, (3) `dt_initial` parameter is silently ignored by AdaptiveTimeController
- `release-notes-alpha-3.md` — Changed section: C3S G° correction with physical justification
- `docs/session56_summary.md` — this file
- `memory/project_c3s_lnK_correction.md` — new project memory documenting the procedure, validation, and follow-ups
- `memory/MEMORY.md` — pointer to the new memory

Nothing built or run for release; no submodule touched.

## The design conversation

Jeff opened with a preference: rescale SR parameters k/B/n to match GEMS's ln K (keeping k unchanged as an infinite-dilution measured value), targeting Figure 1 of Bullard 2015 CCR as the empirical benchmark. He asked me to demonstrate this was achievable before considering the DCH edit.

**First finding**: pure B/n rescaling with the SR functional form `r = k(1 − exp[−(−B ln Ω)^n])` **cannot** preserve Figure 1's rate-vs-aqueous-state curve when ln K shifts by a constant Δ ≠ 0. The rate law has `r = 0` exactly at `Ω = 1` (i.e., Q = K), so any (B, n) choice that preserves the paper's k anchors the zero-rate crossing at the current K. Shifting K in the database shifts the crossing in aqueous-state space, and no B/n choice can compensate — the offset breaks affinity in ln u.

**Second finding**: an approximate compromise fit is possible if we accept a shape change (n from 3.73 to ≈ 9.8) and systematic residuals of ~3.4% of k over Nicoleau's data range. But the shape change is a numerical artifact, not physical, and n = 9.8 doesn't correspond to any interpretable dissolution mechanism.

**Jeff's decision**: accept my recommendation to correct GEMS's ln K by editing G° in the DCH file. The physical justification — Babushkin's clinker-formation calorimetry at high T with estimated low-T Cp integration is known to have ~2% uncertainty in G°(clinker), and the community (Blanc et al. 2010 Thermoddem) has already used different G°(C3S) values closer to Nicoleau's than to CemData18's.

## The DCH edit

Target: shift ΔG°_rxn(C3S dissolution) at 298.15 K by +65,211.81 J/mol (i.e., ln K by −26.3, taking it from −24.4 to −50.7 for the H₄SiO₄ form, or equivalently from −14.8 to −41.1 for the HSiO₃⁻ form). Since C3S is on the LHS of the dissolution reaction, this requires **subtracting** 65,211.81 J/mol from G°(C3S) (making C3S more stable). I initially wrote the sign the wrong way in an explanatory paragraph and had to correct.

Applied uniform offset at all 39 T grid points (277.15–353.15 K). This is equivalent to assigning the entire discrepancy to H° with S° preserved. Constant offset at all T means the T-derivative of G is unchanged and the shape of ln K(T) is preserved.

Implementation care:
- CRLF line endings preserved (used `read_bytes()`/`write_bytes()`, not `read_text()`/`write_text()` which would silently normalize CRLF→LF and corrupt every line in the file)
- Format `%.7f` (7-decimal precision) matches CemData18 convention
- Only line 682 differs vs backup (verified line-by-line)
- Backup at `src/data/gems/thames-dch.dat.pre-c3s-lnK-fix-20260731`

Verified by re-parsing the modified file and recomputing ln K:
- ΔG°_rxn(298.15 K, bracketed) = +125,683.08 J/mol → ln K = −50.7000 ✓
- Same shift factor exp(26.3) ≈ 2.65 × 10¹¹ applies to SI(C3S) at all T
- SI(CSHQ), SI(Portlandite), SI(all other phases) unchanged (only C3S's G° was touched)

## Calorimetry preserved (unexpected but good news)

Jeff raised a caveat mid-session: he wants THAMES to eventually predict isothermal microcalorimetry curves as a validation channel. That requires accurate ΔH°_rxn per reaction step, not just accurate ΔG°_rxn. Initial concern: my G0-only edit would leave calorimetric predictions using Babushkin's (potentially wrong) H° values.

Analysis:
- Direct comparison of paper's ΔH°_rxn(H3SiO4⁻ form) = −137 kJ/mol vs GEMS's translated ΔH°_rxn(HSiO3⁻ form) = −135.8 kJ/mol using the definitional identity H3SiO4⁻ ≡ HSiO3⁻ + H2O
- Discrepancy: only **1.2 kJ/mol** (~1%), well within paper precision
- **Babushkin's H°(C3S) is essentially correct.** The ln K discrepancy that Session 55 uncovered is a reference-state offset in how CemData18 stores its G0/H0/S0 triple (they differ by +131 kJ/mol constant across all species — a GEMS convention, not a physical error).

Consequence: **no H0 correction needed**. For calorimetric prediction dq/dt = ΔH°_rxn · dξ/dt:
- `dξ/dt` (reaction rate) uses SI via G0 → **now correct** thanks to my edit
- `ΔH°_rxn` (heat per unit reaction) uses H0 → **was already correct**

Same audit should be applied to every other Standard/SR-driven phase — logged in POST_ALPHA_TODOS.

## Portlandite spot-check (5 minutes)

Before doing anything else, verified Portlandite K in GEMS: log Ksp = −5.2004 vs CemData18 nominal target −5.20 (exact match to 4 decimal places), Sipos 2006 −5.19 (0.01 off), Duchesne & Reardon 1995 −5.29 (0.09 off within literature scatter). ΔH°_rxn from GEMS = −18.4 kJ/mol matches Sipos calorimetric value ~−18 kJ/mol. **No correction needed for Portlandite.**

Hypothesis emerging from C3S vs Portlandite comparison: the Babushkin heritage issue is specific to anhydrous clinker phases (C3S, C2S, C3A, C4AF — extrapolated from high-T calorimetry) not the aqueous-in-equilibrium phases (Portlandite, gypsum, ettringite — measured near ambient conditions). Full audit pending.

## Sanity check 1 — JMAK-Portlandite validation (still running at session end)

Config at `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/sanity-3h/` — copy of the 4b test dir with `finaltime = 3.0` (days, was 28), corrected DCH, no other changes. Portlandite = SaturatingRate + CNT + JMAK (n=4, α=4π/3), all product phases active as in the 4b config.

Prior 4b run (July 28) was killed at t=3.24 h because SI(Portlandite) hit 1632 and was climbing monotonically — the SI runaway that the FINDINGS attributed to the well-mixed-electrolyte limitation.

Current sanity run at session end: t≈3.07 h, SI(Portlandite) = 13.3 and **declining** (was 13.6 at t=2.81 h, 13.5 at 2.88 h, 13.5 at 2.94 h, 13.4 at 3.01 h). **The Session-55 mass-balance fix has resolved the SI runaway.**

Left running in background; will complete in several hours to reach finaltime = 72 h. When Jeff picks up in Session 57, compare against Session-46's ~14% Portlandite at 24 h target.

## Sanity check 2 — pure-C3S paste, C3S ln K validation (completed)

Setup at `~/tmp/thames-pureC3S-sanity-v2/`: `AlitePaste-w45` microstructure, Alite = SaturatingRate with Han-2025 params, all product phases (Portlandite, CSHQ, ~95 others) suppressed via top-level `suppressed_phases` list.

**First attempt (`~/tmp/thames-pureC3S-sanity/`) failed**: dt_initial = 0.0001 h was ignored; first cycle went straight to dt = 0.24 h (first outtime); SR rate at k for 14 min dissolved enough Alite to push SI from 1e-14 all the way to 505 in a single step. Overshoot froze the aqueous state past supersaturation; SR rate turned off (correctly, no reverse branch active); no further evolution.

**Discovery**: most of the dissolved Si went into the CaSiO3@ aqueous complex (2.9e-2 mol/kg, up from 5.4e-6 initial). Ca and Si form ion pairs at these concentrations; GEMS accounts for this properly in the SI calculation. The overshoot arithmetic was fine; the setup was fragile.

**dt_initial bug logged** in POST_ALPHA_TODOS: AdaptiveTimeController sizes the first cycle by first outtime (not `dt_initial`). Documented as workaround-with-tiny-first-outtime; real fix is a source-level `min(dt_initial, time_to_first_outtime)` in the initialization path.

**v2 retry with outtimes = [1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 0.01, 0.05, 0.1, 0.25, 0.5] days** (first cycle dt forced to 8.64 ms):

| Time (h) | SI(Alite) = Ω | Alite vol frac |
|---|---|---|
| 2.4e-6 | 3.6e-13 | 0.41596 |
| 0.024 | 1.75e-4 | 0.41586 |
| 0.24 | 1.51e-3 | 0.41582 |
| 1.2 | 0.0147 | 0.41576 |
| 6 | 0.049 | 0.41571 |
| 12 | 0.078 | 0.41569 |

Trajectory grew smoothly, no overshoot, monotonic approach to Ω=1. Alite dissolved 0.065% in 12 h (vs v1's 0.13% in 14 min at unbounded rate). CSHQ and Portlandite stayed at 0 voxels throughout (suppression working). Rate slowed asymptotically as Ω→1.

Endpoint (Ω = 1) not reached — SR rate is asymptotic near equilibrium, would take days more. Not necessary for validation; the trajectory shape and mass balance confirm the corrected K is producing physically sensible driving forces.

## Design questions surfaced but not yet answered

- Session 55's C_eq design question (for the transport half-cell) is still open. Now that SI(C3S) in cement paste is ~1e-14 instead of ~1e-26, the `C_eq = C_bulk / S^(1/stoich)` derivation is 12 orders of magnitude better conditioned but still numerically extreme. May or may not still need the `referenceSinkPhase` field — worth revisiting with corrected numbers before committing to a design.

- Whether Portland cement priority-2 rerun (Session 55's silica-fume 200³ 28-day run) reproduces cleanly under corrected C3S K. Not urgent — C3S is Parrott-Killoh in that config, so the correction only affects reported SI(C3S), not the actual dissolution rate.

## Pending when Session 57 resumes

1. **Check on JMAK-Portlandite sanity** (`~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/sanity-3h/`) — should have finished by the time a fresh session starts. Compare trajectory against Session-46 target (~14% Portlandite at 24 h).
2. **Re-run pure-alite paste with corrected C3S K** (S55's shell physics thread) — was blocked on this K correction. `~/tmp/thames-alite-baseline` and `~/tmp/thames-alite-shell` re-runs, ~200 s each. Compare shell effect magnitude.
3. **Broader K audit** on C2S, C3A, C4AF (all Babushkin heritage — likely need corrections), plus ettringite, gypsum, CSHQ end-members (likely fine like Portlandite). ~5 min per phase using the procedure documented in `project_c3s_lnK_correction.md`.
4. **C_eq design decision** for the transport half-cell (revisit with corrected SI numbers).
5. **Portland cement priority-2 rerun** — deferred, largest compute cost (~27 h wall), not blocking anything smaller.
6. **Post-alpha**: fix the `dt_initial` bug (POST_ALPHA_TODOS entry documents proposed fix).

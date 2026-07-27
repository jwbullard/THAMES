# CNT Integration — Design Decisions & Calibration

Consolidation of the design rationale, calibration story, and scope
decisions from the CNT integration thread (Sessions 50–51, 2026-07-20
through 2026-07-24). This document is a **historical reference** — for
current implementation state see `CNT_ARCHITECTURE.md`; for outstanding
work see the follow-on entries in `POST_ALPHA_TODOS.md`.

Companion memory pointers:
- `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/project_cnt_kinetics_integration.md`
  — CNT thread history and step-by-step outcomes.
- `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/project_saturating_rate_model_next.md`
  — the follow-on Han et al. Eq. 7 rate-law work.
- `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/reference_cnt_prototype_notebook.md`
  — the Python calibration notebook.

---

## 1. Motivation

THAMES's existing kinetic models had two failure modes for phases that
begin at zero mass:
- `ParrotKillohModel` absorbs nucleation phenomenologically into the
  Avrami-Cottrell fit — works for portlandite but is not extensible to
  new chemistries.
- `StandardKineticModel` and `PozzolanicModel` produce zero rate when
  surface area is zero and non-zero rate the instant a phase has any
  mass. In practice this means phases either never form or form
  instantly when GEMS says so — neither is right for what-if exploration
  with new SCMs, activators, or alternative binders.

CNT adds a mechanistic nucleation term with user-adjustable parameters,
matching Jeff's "what-if exploration tool that morphs into a predictive
tool as data come online" philosophy.

**Exclusion**: Parrot-Killoh phases do NOT get CNT. Adding it on top of
the Avrami-Cottrell fit would double-count nucleation.

## 2. The 8-step plan (final status)

| # | Step | Status |
|---|---|---|
| 1 | Python calibration prototype (notebook) | ✅ |
| 2 | JSON schema design | ✅ |
| 3 | Scaffold parameters (parser + optional member) | ✅ |
| 4 | CNT rate calculation (pure math + standalone test) | ✅ |
| 5 | Batched placement + CNT-driven adaptive dt cap | ✅ |
| 6 | Portlandite CNT physics test | ⚠️ ran but dt collapse motivated SaturatingRateModel deferral |
| 7 | Extend CNT to PozzolanicModel | ✅ (with mid-step correction: no interface gating) |
| 8 | Silica-fume validation | ✅ (pipeline functional; failure mode changed vs Session-46) |

## 3. Locked design decisions (Session 50)

- **Anonymous accumulator per phase, batched placement.** One scalar
  volume accumulator per nucleating phase. Each cycle increment by
  `J · V_e · dt · V_crit`. When the accumulator ≥ `V_voxel`, place
  `floor(accumulator / V_voxel)` voxels simultaneously at independently
  drawn random locations. Each placed voxel implicitly absorbs the
  post-critical sub-voxel-scale growth that occurred while the
  accumulator was building.

- **NOT per-voxel per-phase fractional occupancy.** Would require
  rewriting `Site.h`, `Interface.cc`, `Lattice.cc`, VTK/PNG export,
  `ElasticModel`, ITZ detection, and adjacency counting. Explicitly
  rejected as scope creep. Sub-voxel fractional fill is transport-
  kinetics-thread territory, not CNT.

- **Placement locations for portlandite v1: uniform-random over
  ELECTROLYTEID voxels** (homogeneous). Substrate voxels for later
  heterogeneous phases. Preference for locally-elevated S requires
  the transport-kinetics thread's spatially-resolved electrolyte and
  is deferred.

- **CNT drives adaptive dt via cap — predict-then-shrink, not silent
  cap.** If `N_want > N_cap` at the proposed dt, shrink dt so
  `N_want ≈ N_cap` at the shrunk dt. Silent hard capping discards
  moles and biases the S estimate. Accumulator-carried excess is fine
  only as a hard safety fallback if required dt drops below the
  `stepTimeTHR_` floor. `N_cap` target: 1–5% of electrolyte voxel count
  (default 2%) so the fixed-J-within-cycle assumption holds.

- **Framework preserves θ knob for later heterogeneous phases** even
  though portlandite pins θ = 180°. Same code path for both regimes;
  the placement branch selects on θ (implemented as
  homogeneous-only-so-far).

- **Every CNT parameter exposed as user-adjustable JSON with
  `value` / `range` / `provenance` fields**. Nothing hardcoded in C++.
  The parser reads only `value`; `range` is user-tunable envelope for
  sweep tools; `provenance` is a curation trail for humans.

- **Global `useNucleationKinetics` opt-in (default false).** All CNT
  machinery is inert with this off, regardless of per-phase blocks.

## 4. Calibrated portlandite defaults

| Parameter | Value | Range | Provenance |
|---|---|---|---|
| γ | 0.044 J/m² | 0.030 – 0.070 | Basal-plane habit. DFT vacuum surface energies for Ca(OH)₂ basal plane are ~0.25 – 0.35 J/m² (Galmarini et al., Cem. Concr. Res. 2011). Experimental **solid–liquid interfacial** energies γ_(s-l) for portlandite in aqueous solution — from induction-time analysis in cement pastes (e.g., Garrault/Nonat/Scherer literature) — sit in the ~0.03 – 0.10 J/m² range. The ~10× empirical ratio between DFT-vacuum and aqueous-measured values reflects a combination of dielectric screening of the electrostatic contribution, hydration structure at the interface, and surface reconstruction; it should not be attributed to dielectric screening alone. The 0.044 J/m² value bisected at A₀ = 1e30 to give onset S ≈ 4.6 in C3S paste (Session-50 prototype, pre-fix pipeline) sits well within the aqueous experimental envelope.|
| θ | 180° (pinned) | 1 – 180 | Homogeneous limit; SEM shows Ca(OH)₂ nucleating near but not on C3S surfaces (JWB observation) |
| A₀ | **1e25 /(m³·s)** (interim, 2026-07-27) | 1e22 – 1e32 | Session-50 originally recommended 1e30 /(m³·s) based on Kashchiev textbook order. After the CNT scaling fix landed 2026-07-27, that value produced ~32 % Portlandite by 1 h in Portland paste (vs Session-46 archive ~14 % at 24 h). Reduced to 1e25 as a bounded-behavior placeholder. **Pure-A₀ recalibration cannot recover Session-46-style trajectories** because SR growth is exponential-in-mass once nuclei exist; the correct fix requires Option (c) — see `docs/POST_ALPHA_TODOS.md` "CNT Portlandite calibration ..." for the full analysis. |
| V_m | 33.08 cm³/mol | fixed | GEMS CemData18 at 298 K (comes from GEMS at runtime) |
| T | 298.15 K | 277 – 353 | GEMS thermodynamic-database supported range |

γ and A₀ are **jointly constrained but individually degenerate** — the
feasibility ridge in the prototype notebook's Cell 17 shows a family of
(γ, A₀) pairs that all reproduce the empirical S ≈ 4–5 onset (in the
prototype's simplified model). Independent constraint on either
requires a measured induction time under known S(t), which we do not
currently have. Both must remain user knobs.

Basal-plane cleavage energy for Ca(OH)₂ in vacuum is ~0.25 – 0.35 J/m²
per DFT calculations (Galmarini et al., Cem. Concr. Res. 2011).
Experimental **interfacial** energies γ_(s-l) for portlandite in
aqueous solution — extracted from induction-time analysis in cement
pastes (Garrault, Nonat, Scherer, and others) — are in the
~0.03 – 0.10 J/m² range. The ~10× ratio between DFT-vacuum surface
energy and measured aqueous interfacial energy reflects dielectric
screening of electrostatics AND hydration-structure energetics AND
surface-reconstruction effects, not any single mechanism. The
calibrated 0.044 J/m² sits well within the aqueous experimental
envelope.

**About the A₀ change from 1e30 to 1e25.** The Session-50 A₀ was
calibrated against a broken production pipeline (Session-51 CNT
placement had a ~10⁷× scaling bug plus a missing microPhaseVolume_
sync; both fixed 2026-07-27 — see `POST_ALPHA_TODOS.md`). With the
fix landed, the same A₀ = 1e30 produced ~50 000–70 000 Portlandite
voxels per cycle at Portland-paste SI ~ 10, and Portlandite reached
32 % by 1 h. A sweep across A₀ ∈ {1e30, 1e26, 1e24, 1e22, 1e10}
showed no single A₀ recovers Session-46's ~14 %-at-24-h trajectory:
too high → overshoot from CNT over-placement plus SR area-catalyzed
runaway; too low → SR area too small, SI accumulates unphysically to
>100. The 1e25 value lands in a "bounded but still fast" regime that
does not match Session-46 in absolute rate but does not exhibit
either failure mode either. The physical fix is Option (c).

## 5. Sanity numbers at the calibrated defaults

200³ RVE, 50% porosity, V_voxel = 1 μm³, dt = 0.01 h = 36 s, θ = 180°:

| S | ln S | r* [nm] | ΔG*/kT | J [1/(m³·s)] | log₁₀(N/cycle) |
|---|---|---|---|---|---|
| 2.0 | 0.693 | 1.69 | 128.5 | 1.5×10⁻²⁶ | −43.3 |
| 4.5 | 1.504 | 0.78 | 27.3 | 1.4×10¹⁸ | −0.4 (onset) |
| 10.0 | 2.303 | 0.51 | 11.6 | 8.8×10²⁴ | 5.85 |
| 50.0 | 3.912 | 0.30 | 4.04 | 1.8×10²⁸ | 8.5 |

Verified against both the Python prototype's Cell 5 and the C++ Step-4
free functions at build time via `src/unit_tests/test_nucleation_rate.cc`.
These are the numbers the standalone test asserts against ±0.5 log₁₀
tolerance.

**Historical note**: an earlier version of the project memory recorded
the S=2 sanity value as "~10⁻⁵⁵". That number was the `exp()` argument
(ΔG*/kT), not the voxels-per-cycle result. Corrected during Step 4
verification.

## 6. Anti-patterns caught during design

- **Do NOT lead with "hard-cap" language when discussing the runaway-N
  regime.** Cap-driven dt reduction (Option C in Session-50 notes) is
  the correct control response; capping is only a safety fallback for
  when the required dt would drop below `stepTimeTHR_`. The prototype's
  original findings section made this mistake and Jeff caught it. The
  language should always be "cap tightens dt" not "cap discards nuclei."

- **Do NOT gate CNT by same-phase interface size** (Step-7 correction).
  The Session-50 memory said this would prevent double-counting the
  Pozzolanic "empirical acceleration parameters." That characterization
  was wrong on two counts: (1) the Pozzolanic Ca/Na/K Langmuir adsorption
  + OH activity + water activity + LOI + sio2 terms are Dove/Crerar
  lineage **fundamental** dissolution kinetics, not empirical
  acceleration ramps; (2) CNT continuous nucleation should always be
  permissible when S is high enough and sites are available. Site
  saturation is a different regime, indexed by substrate-voxel count for
  heterogeneous nucleation, not same-phase interface. Fix: Standard and
  Pozzolanic have symmetric CNT eligibility. Site-saturation gating for
  θ<180° is deferred to POST_ALPHA_TODOS.md.

- **Do NOT sidestep to develop `SaturatingRateModel` mid-CNT-thread.**
  Step-6 revealed that Standard's Eq. 6 rate-law divergence at high Ω
  causes the observed dt collapse. The right cure is Han et al. Eq. 7
  (`SaturatingRateModel`), but adding a new kinetic model class within
  the CNT thread would entangle two conceptually distinct projects.
  Scope decision (2026-07-23): close CNT thread with Standard as-is;
  open a new thread for SaturatingRateModel; re-run Step 6 Portlandite
  validation once it lands.

## 7. Working protocol Jeff established

- Plan before edit: state files touched, what changes, what could break.
- One focused edit per step; no drive-by refactoring.
- Build after every C++ change.
- Standalone math test must stay green after every build.
- CNT-off parity check must stay byte-identical to baseline after every
  build.
- Jeff drives all git operations; the assistant does not commit or push.
- C++ work happens from `backend/thames-hydration/` (the submodule), never
  edited through the super-repo view. When time to commit, the submodule
  pushes first, then the super-repo pointer commit follows.

## 8. Handoff to future work

- **`SaturatingRateModel` thread — LANDED 2026-07-24.** Han et al. Eq. (7)
  `r = k (1 − exp[−(−B ln Ω)^n])` implemented as a fourth `KineticModel`
  subclass alongside Standard, Pozzolanic, ParrotKilloh. Asymmetric
  dissolution / precipitation parameter blocks supported (precipitation
  optional; falls back to dissolution values with a one-time log line
  per phase). CNT hooks symmetric with Standard/Pozzolanic. Portlandite
  calibration: k = 4.05×10⁻⁴ mol/m²/s at 24 °C, B = 0.74, n = 1.9,
  ΔH‡ = 13.9 kJ/mol from Han et al. 2025 CEJ. Details in
  `docs/SATURATING_RATE.md`. Validation:
  `~/tmp/thames-satrate-val/saturating_rate_validation.md` — resolved
  the Step-6 6b dt-collapse pathology on the Portlandite baseline.

- **UI CNT parameter input** — Hydration Panel editor for the
  per-phase nucleation block, top-level `useNucleationKinetics`, and
  `nucleationCapFraction`. Currently JSON-only. Tracked in
  `POST_ALPHA_TODOS.md`.

- **Heterogeneous CNT site-saturation gating** — when the first phase
  with θ<180° is configured (C-S-H, ettringite, etc.), the rate
  calculation must bound N by available substrate voxels, not just
  N_cap. Tracked in `POST_ALPHA_TODOS.md`.

- **Vocabulary hygiene** — `Pi` → `PI`, `limitICTHRESH` →
  `LIMITICTHRESH`, `affinity` rename in Lattice/Isite/Interface (NOT
  ChemicalSystem or GEMS3K — both use "affinity" correctly in the
  thermodynamic driving-force sense). Tracked in `POST_ALPHA_TODOS.md`.

# CNT Integration — Implementation Architecture

Reference document for the Classical Nucleation Theory (CNT) integration
into the THAMES C++ hydration engine. This document describes **the
implementation, not the theory** — for CNT physics see the group's
reading list (Kashchiev, Han et al. 2025 CEJ, and the Session-50
prototype notebook at
`~/Research/THAMES-Tests-2026/Scripts/NucleationCNT-Prototype.ipynb`).

Companion documents:
- `docs/CNT_DESIGN_DECISIONS.md` — the historical rationale for
  design choices, calibrated portlandite defaults, sanity numbers, and
  scope decisions. Read this if you want to know *why* the pieces are
  shaped this way.
- `docs/POST_ALPHA_TODOS.md` — deferred CNT-related work items.

Scope: what each file does, what each guard prevents, how the pieces
coordinate cycle-by-cycle.

---

## 1. File responsibilities

| File | Role |
|---|---|
| `src/thameslib/NucleationParameters.h` | POD struct holding γ, θ, A₀ for one phase |
| `src/thameslib/NucleationRate.h/.cc` | Pure-math free functions in `namespace cnt` — no state, no `this`, no hidden dependencies. Unit-tested standalone. Handles molar-volume → per-molecule conversion internally. |
| `src/thameslib/PhysicalConstants.h` | `BOLTZMANNCONSTANT`, `AVOGADROCONSTANT`, `Pi`, `GASCONSTANT`. Extracted so pure-math modules can consume them without pulling in GEMS/nlohmann. |
| `src/thameslib/KineticData.h` | Adds `std::optional<NucleationParameters> nucleation` — the parse-time carrier |
| `src/thameslib/KineticModel.h` | Base-class virtual method declarations (default: no-op), so `KineticController` can iterate polymorphically |
| `src/thameslib/StandardKineticModel.h/.cc` | Per-phase CNT state (`nucleation_`, accumulator) + rate computation + zero-mass bypass |
| `src/thameslib/PozzolanicModel.h/.cc` | Symmetric to Standard — same members, same rate calc, same bypass |
| `src/thameslib/SaturatingRateModel.h/.cc` | Bullard 2015 / Han 2025 Eq. 7 saturating rate law; same four CNT virtuals as Standard/Pozzolanic. Alternative to Standard when the phase needs SI ≫ 1 handling without Eq-6 divergence. See `docs/SATURATING_RATE.md`. |
| `src/thameslib/SaturatingRate.h/.cc` | Pure-math free functions in `namespace sat` — dissolution/precipitation rates and Arrhenius scale. Unit-tested standalone. |
| `src/thameslib/SaturatingRateParameters.h` | POD struct holding rateConstant / B / n for one direction (dissolution or precipitation) |
| `src/thameslib/KineticController.h/.cc` | Per-cycle orchestration: pre-loop CNT-lock, cap check, placement, mass-balance update |
| `src/thameslib/Controller.h/.cc` | Reads global CNT flags from simparams.json; wires the CNT-based dt cap into the two dt-selection sites |
| `src/unit_tests/test_nucleation_rate.cc` + `build_and_run.sh` | Standalone math regression test — zero external dependencies |

## 2. JSON schema (complete example)

Top-level `simparams.json`:
```json
{
  "useNucleationKinetics": true,
  "nucleationCapFraction": 0.02,
  "microstructure": { "phases": [ ... ] }
}
```

Per-phase `kinetic_data.nucleation` block (add to any Standard- or
Pozzolanic-model phase to enable CNT for that phase):
```json
"nucleation": {
  "gamma": {
    "value": 0.044,
    "range": [0.030, 0.070],
    "provenance": "Basal-plane habit; calibrated to onset S~4.6 in C3S paste"
  },
  "theta": {
    "value": 180,
    "range": [1, 180],
    "provenance": "Homogeneous limit; SEM shows Ca(OH)2 nucleating near but not on C3S surfaces"
  },
  "A0": {
    "value": 1.0e30,
    "range": [1.0e28, 1.0e32],
    "provenance": "Kashchiev textbook order for solution nucleation"
  }
}
```

Parser reads only the `value` field of each parameter. `range` and
`provenance` are curation metadata for humans and sweep tooling — they
never enter simulation memory. Missing `nucleation` block = CNT disabled
for that phase. Missing top-level `useNucleationKinetics` = defaults to
false (fully disabled).

`theta` is an integer in [1, 180]. `theta = 180` triggers homogeneous
placement (uniform-random over electrolyte voxels via
`Lattice::nucleatePhaseRnd`). `theta` in [1, 179] is reserved for
heterogeneous placement on substrate voxels — the code path exists but
substrate selection logic will land in a later work item; the placement
call currently always uses `nucleatePhaseRnd`. This is not a bug; it
means θ<180 is functionally equivalent to θ=180 at present.

## 3. Data flow, one cycle

```
    simparams.json
         │
         ▼
    Controller::parseDoc              (top-level CNT flags)
    KineticController::parseKineticData -> parseNucleationBlock
         │                            (per-phase nucleation → KineticData)
         ▼
    StandardKineticModel / PozzolanicModel constructor
         │                            (nucleation_ = kineticData.nucleation)
         ▼
    -- per-cycle loop --
         │
    Controller chooses dt:
       min( adaptive.getNextTimestep(),
            computeKineticsBasedMaxTimestep(),
            computeNucleationBasedMaxTimestep() )   -- ▲ CNT cap here
         │
         ▼
    KineticController::calculateKineticStep
         │
         ├── (a) Pre-loop CNT-lock
         │     For each phase with hasNucleation() && scaledMass<=0.0,
         │     set DCLowerLimit = DCUpperLimit = 0. Prevents GEMS from
         │     spontaneously precipitating zero-mass CNT phases.
         │
         ├── (b) For each kinetic model:
         │       (b1) Model::calculateKineticStep
         │            -- Standard/Pozzolanic early-return bypass fires
         │               if nucleation_.has_value() && scaledMass<=0.0
         │       (b2) Kinetic-controlled DC bookkeeping, impurities, etc.
         │       (b3) CNT placement block (end of loop iteration):
         │              dN = model->computeNucleationVoxels(dt_hours)
         │              model->accumulateNucleation(dN)
         │              nWant = model->drainNucleationInteger()
         │              if nWant > 0:
         │                nPlaced = Lattice::nucleatePhaseRnd(phaseId, nWant)
         │                DCMoles_[dcId] += nPlaced * V_voxel / V_molar
         │                setDCLowerLimit(dcId, DCMoles_[dcId])   (▲ lock!)
         │                setDCUpperLimit(dcId, DCMoles_[dcId])
         │
         ▼
    Commit DCMoles_ -> ChemSys      (for i in DCs: chemSys_->setDCMoles(...))
         │
         ▼
    GEMS equilibration              (respects the locked DC limits)
         │
         ▼
    Lattice::changeMicrostructure   (writes updated microstructure)
```

## 4. Guards — what each one prevents

| # | Guard | Location | Prevents |
|---|---|---|---|
| G1 | `!nucleation_.has_value()` → return 0.0 in `computeNucleationVoxels` | Standard/Pozzolanic .cc | Phases without a CNT block from having any effect |
| G2 | `S <= 1.0` → return 0.0 in `computeNucleationVoxels` | Standard/Pozzolanic .cc | Nucleation when there's no thermodynamic driver |
| G3 | Early-return bypass: `nucleation_.has_value() && scaledMass <= 0.0` at top of `calculateKineticStep` | Standard/Pozzolanic .cc | Standard's `area = 1.0` fallback (`.cc:188`) from spontaneously precipitating a zero-mass CNT phase; also prevents Pozzolanic's `initScaledMass_ > 0.0` throw |
| G4 | Pre-loop CNT-lock: sets DC upper/lower limits to 0 for zero-mass CNT phases | KineticController.cc, in `calculateKineticStep` before phase loop | GEMS from precipitating a CNT-controlled phase on its own accord (bypassing the model) |
| G5 | Post-placement DC-limit raise to `DCMoles_[dcId]` | KineticController.cc, inside placement block | GEMS from immediately dissolving CNT-placed nuclei back to the pre-CNT floor |
| G6 | `!useNucleationKinetics_` → return dtProposed unchanged in `computeNucleationBasedMaxTimestep` | KineticController.cc | The CNT dt cap from firing when CNT is globally disabled |
| G7 | Global `useNucleationKinetics_` gate on the CNT placement block | KineticController.cc, in phase loop | Any placement machinery from running when CNT is globally disabled |
| G8 | `initKineticData` resets `kineticData.nucleation` | KineticController.h | One phase's nucleation block from leaking into the next phase during parsing (silent data corruption if omitted) |

G3 + G4 must fire together for the "CNT is the sole path to bootstrap a
phase from mass = 0" invariant to hold. If either is bypassed, the phase
can bootstrap via the model's normal path or via a GEMS-driven side
channel, and CNT loses its role as the nucleation-only mechanism.

G5 must fire on every placement. Without it, GEMS uses the stale
`keepNumDCMoles`-computed lower limit as its floor and dissolves the
newly placed nuclei back in the same cycle.

## 5. Cap rationale

CNT rate `J` is fixed within a cycle (uses S from the previous
equilibration). The estimated voxel count for a given `dt` scales
linearly. If `dt` is too large, the fixed-J-in-cycle approximation
breaks down because the placement itself drops the solute enough to
change J materially.

The cap keeps `N_want ≤ N_cap` where `N_cap = capFraction ×
count_[ELECTROLYTEID]`. Default `capFraction = 0.02` — 2% of the
current electrolyte-voxel count per cycle. When a phase's `N_want`
exceeds `N_cap` at the proposed dt, `computeNucleationBasedMaxTimestep`
shrinks dt so `N_want == N_cap` at the shrunk dt (linear scaling).

The cap is **per-phase**: iterate over kinetic models, each phase whose
CNT would overshoot contributes a per-phase shrunk dt, and the minimum
across phases wins. Same idiom as `computeKineticsBasedMaxTimestep`.

The cap composes with the existing kinetics cap via sequential `min` at
both Controller dt-selection sites (success path around line 812,
post-failure path around line 740). Order: adaptive controller proposes
dt, kinetics cap tightens, CNT cap tightens further. The final dt is
`min(adaptive, kinetics, cnt)`.

## 6. Design decisions worth calling out

- **Rate math as free functions in `namespace cnt`, not member methods.**
  Zero hidden state means the standalone test can call them with
  arbitrary inputs — no need to construct a model instance and its
  entire dependency graph just to verify the physics formula.
- **Per-phase accumulator lives on the model instance** (not on
  KineticController). Batched placement (Session-50 spec):
  `computeNucleationVoxels` returns a fractional voxel count each cycle,
  the accumulator collects it, and only whole voxels are drained for
  placement. Fractional remainders carry forward. This preserves total
  moles-per-cycle expectation while placing at integer granularity.
- **Placement uses `Lattice::nucleatePhaseRnd`.** Uniform-random over
  electrolyte voxels — the homogeneous-nucleation case (θ=180°). The
  affinity-weighted `nucleatePhaseAff` is present in Lattice for future
  heterogeneous work but is not wired here.
- **Placement is batched: `floor(accumulator)` voxels are placed
  simultaneously at independently drawn random locations.** Not one
  voxel per cycle. Matches the physical interpretation that each placed
  voxel represents the critical nucleus plus the sub-voxel-scale growth
  that occurred while the accumulator was building.
- **Molar volume comes from GEMS; conversion to per-molecule is hidden.**
  Callers pass `chemSys_->getDCMolarVolume(dcId)` (units m³/mol). The
  `cnt::` free functions divide by Avogadro internally so the CNT
  formulas (with `k_B`, not `R`) get the per-molecule volume they
  actually need. This keeps caller code simple and prevents unit-mismatch
  bugs.
- **`ChemicalSystem::getMicroPhaseSI` returns the linear ratio, not
  log₁₀.** GEMS internally uses log₁₀ but THAMES converts at
  `ChemicalSystem.cc:3244` via `pow(10, Ph_SatInd(...))`. Every CNT
  call passes the value straight through without a log conversion —
  the comment at the fetch site flags this so nobody re-does the
  conversion.
- **Standard and Pozzolanic have symmetric CNT eligibility.** Both fire
  CNT whenever `nucleation_.has_value() && S > 1.0`, regardless of
  same-phase-interface size. Site-saturation gating is a heterogeneous-
  nucleation concern (θ < 180° on scarce substrate voxels), not a
  same-phase-interface concern, and belongs to a later work item.
- **`useNucleationKinetics` is a hard global kill switch** — with it
  false, all CNT machinery is inert regardless of per-phase blocks.
  Simplifies A/B comparisons and makes "disable CNT quickly" a one-key
  change to simparams.json.

## 7. Verification points that any change must not break

- `src/unit_tests/build_and_run.sh` — standalone math test still exits 0.
- CNT-off parity — a config with `useNucleationKinetics = false` (or
  absent) and no nucleation blocks anywhere must produce output byte-
  identical to a pre-CNT baseline. Prior verifications used the Step-3
  scratch dir `~/tmp/thames-step5-parity/HY-ccr152-ws45-nuc-accept`.
- Clean build with no new warnings.

## 8. Known limitations documented in POST_ALPHA_TODOS.md

- UI CNT parameter input — Hydration Panel editor for the nucleation
  block, top-level switch, and cap fraction.
- Site-saturation gating for heterogeneous CNT (θ < 180°) — substrate-
  voxel-count bound on N_want, to be added when the first phase with
  θ<180° is configured.
- Vocabulary hygiene — `Pi` → `PI` etc. alongside the pending `affinity`
  rename in `Lattice`/`Isite`/`Interface` (not `ChemicalSystem` or
  GEMS3K, both of which use "affinity" correctly).
- Full-hydration validation — motivated by Step 6/8 dt-collapse. Requires
  the `SaturatingRateModel` implementation of Han et al. Eq. (7). See
  `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/project_saturating_rate_model_next.md`
  for the follow-on plan.

# Session 50 — Classical Nucleation Theory: Design, Calibrated Prototype
July 20, 2026 — macOS

Opened a new multi-session thread to add classical nucleation kinetics
(CNT) to the THAMES C++ hydration engine, targeting `StandardKineticModel`
and `PozzolanicModel` (explicitly excluding Parrot-Killoh, which already
absorbs nucleation phenomenologically via Avrami-Cottrell). Design
conversation first; step 1 (Python calibration prototype for portlandite)
built and executed end-to-end in the same session. No C++ touched — Jeff
explicitly held C++ edits until after review.

## Repo-structure refresher

`backend/thames-hydration/` is a git submodule
(`https://github.com/jwbullard/THAMES-Hydration.git`, currently on `main`
at `c6f84fb`, Session 38). Contains the C++ hydration engine:
`src/thames.cc`, `src/thameslib/` (KineticController, KineticModel,
ParrotKillohModel, PozzolanicModel, StandardKineticModel, Controller,
Lattice, ChemicalSystem, GEMS coupling), plus vendored
`GEMS3K-standalone`. `backend/src/` at the top level (NOT a submodule) is
legacy VCCTL C code (`elastic.c`, `micgen.c`) — different subsystem,
unrelated to hydration. CNT work will land inside the submodule.

Workflow reaffirmed for this thread: edit inside the submodule directory,
push submodule first, then commit the pointer change in the super-repo.

## Design conversation (verbatim decisions)

### CNT integration plan — 8 steps

1. **Python prototype** — COMPLETE this session
2. **JSON schema design** — NEXT session
3. Scaffold parameters (compiles, does nothing)
4. CNT rate calculation in `StandardKineticModel` (isolated, unit-testable)
5. Batched random placement + CNT-driven adaptive timestep wiring
6. First end-to-end test on Portlandite (ccr152-ws45 or smaller)
7. Extend to `PozzolanicModel` with same-phase-interface gating
8. Validate against Session 46 silica-fume portlandite oscillation

### Locked-in design decisions

- **Anonymous accumulator per phase, batched placement.** One scalar
  volume-accumulator per nucleating phase, incremented each cycle by
  J·V·dt·V_crit. When accumulator ≥ V_voxel, place
  `floor(accumulator / V_voxel)` voxels **simultaneously at independently
  drawn random locations** and decrement by placed volume. Each placed
  voxel implicitly represents the critical nucleus PLUS the
  post-critical sub-voxel-scale growth that occurred to reach voxel-scale.

- **NOT per-voxel per-phase fractional occupancy.** Explicitly rejected
  as scope creep — would require rewriting `Site.h`, `Interface.cc`,
  `Lattice.cc`, `PngWriter`, VTK export, `ElasticModel`, ITZ detection,
  and adjacency counting. Sub-voxel fractional fill is
  transport-kinetics-thread territory (Session 49), not CNT.

- **Placement locations: uniform-random over electrolyte voxels** for
  portlandite (homogeneous). Substrate voxels for heterogeneous
  nucleation of later phases. Spatial preference for locally elevated S
  requires the transport-kinetics thread's spatially-resolved
  electrolyte and is deferred.

- **CNT drives the adaptive timestep — Option C, not silent capping.**
  If N_want > N_cap for the proposed dt, shrink dt so that
  N_want ≈ N_cap and retry the cycle (same "compute at proposed dt,
  shrink if too aggressive" pattern already used by the kinetic
  maxRelativeChange constraint in `AdaptiveTimeController`). A silent
  hard cap discards moles and biases the S estimate; an
  accumulator-carried excess is fine only as a hard safety fallback if
  required dt drops below the 1e-5 h floor (and should log loudly if it
  fires). N_cap target ~1–5% of electrolyte voxel count so the fixed-J
  assumption within a cycle holds. This is a real change to
  `AdaptiveTimeController` and should be wired up AFTER the isolated
  CNT rate calculation is unit-tested.

- **Framework preserves θ knob** for later heterogeneous phases (C-S-H,
  ettringite) even though portlandite pins θ = 180°. Same code path for
  both regimes.

- **Every CNT parameter exposed as user-adjustable JSON** with `value`,
  `range` (user-adjustable envelope), and `provenance` (curation trail)
  fields. Nothing hardcoded in C++. Consistent with Jeff's
  "what-if exploration tool that morphs into a predictive tool as data
  come online" philosophy.

### Anti-pattern called out

Do NOT lead with hard-cap language as the primary control response for the
runaway-N regime. Cap-driven dt reduction is the correct answer; capping
is only a fallback. This was corrected in the prototype's findings after
Jeff caught it. Should not recur in step 2 discussion or in C++ comments.

## Step 1 — Portlandite prototype notebook

Built and executed at:

- **Notebook:** `~/Research/THAMES-Tests-2026/Scripts/NucleationCNT-Prototype.ipynb`
- **Builder:** `~/Research/THAMES-Tests-2026/Scripts/_build_cnt_notebook.py`
- **Figures:** `~/Research/THAMES-Tests-2026/Figures/CNT-*.png` (6 files)

21-cell notebook with CNT theory block, sensitivity sweeps in γ and A₀,
(γ, A₀) feasibility contour with observed onset band overlaid, defaults
DataFrame, and a 7-item findings section on C++ integration implications.

### Homogeneous formulation (portlandite-specific)

Jeff's observation drove a mid-conversation reformulation. SEM
micrographs show portlandite nucleating *near* C3S surfaces but not *on*
them, though SEM is hard-dried and under vacuum. There is not strong
evidence for heterogeneous nucleation on cement surfaces. Consequence:

- Homogeneous formulation only for portlandite v1
  (J_V per m³ of solution)
- θ pinned at 180° (Turnbull-Vonnegut f(θ) = 1, homogeneous limit)
- γ nudged down to reflect basal-plane habit dominance
- Placement over electrolyte voxels (not substrate voxels)

θ stays a free parameter in the CNT math for later phases; portlandite
just pins it.

### Calibration outcome

Jeff's empirical onset: portlandite appears in C3S paste at ~40 mmol/L
total Ca, corresponding to S = IAP/K_sp ∈ [4, 5]. Convention: S is the
saturation ratio without log (not the GEMS log₁₀ SI convention).

Bisected for γ that puts the 1-voxel-per-cycle threshold at S ≈ 4.5 with
A₀ = 10³⁰ /(m³·s), dt = 0.01 h, 200³ RVE, 50% porosity:

| parameter | value | range | provenance |
|---|---|---|---|
| γ | 0.044 J/m² | 0.030–0.070 | basal-plane habit; DFT est. (Galmarini); calibrated at A₀=1e30 to onset S ≈ 4.6 |
| θ | 180° (pinned) | homogeneous | JWB SEM observation |
| A₀ | 1e30 /(m³·s) | 1e28–1e32 | Kashchiev textbook; jointly degenerate with γ |
| V_m | 33.08 cm³/mol | fixed from GEMS | CemData18 at 298 K |
| T | 298.15 K | 277–353 | GEMS DB range |

γ and A₀ are jointly constrained but individually degenerate — the
feasibility contour (Cell 17) shows any (γ, A₀) pair on the green ridge
reproduces the empirical onset. Without a measured induction time under
known S(t), we cannot separate them. Both must be exposed as user knobs.

Jeff cross-referenced a literature basal-plane cleavage energy for M(OH)₂
in vacuum on the order of 0.25 J/m². Dielectric screening in water
typically drops these by an order of magnitude, so 0.044 J/m² for
water-facing Ca(OH)₂ is in the physically defensible envelope.

### Sanity numbers at the calibrated defaults

- S = 2 → ~10⁻⁵⁵ voxels/cycle (induction period)
- S = 4.5 → ~1 voxel/cycle (onset)
- S = 10 → ~10⁷ voxels/cycle (CNT would demand large dt reduction)
- S = 50 → ~10¹¹ voxels/cycle (unphysical without dt reduction)

The dt-reduction machinery is what protects the model from the S = 10+
regime.

## Session end state

- CNT thread active, step 1 complete, step 2 (JSON schema) queued for
  next session
- Prototype notebook validated (all 6 plots render, defaults land onset
  in observed band)
- Two new memories saved:
  - `project_cnt_kinetics_integration.md` — full plan, step status,
    design decisions, calibrated defaults, anti-patterns
  - `reference_cnt_prototype_notebook.md` — location + build recipe
- MEMORY.md index updated with both pointers
- Zero C++ touched, per Jeff's instruction to hold off until review
- No commits made — Jeff drives git operations

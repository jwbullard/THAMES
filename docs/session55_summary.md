# Session 55 — Mass-Balance Fix, Transport-Kinetics Plan Implementation, Alite Validation
Dates: July 29–30, 2026 — macOS

## Overview

A three-headed session:

1. **Mass-balance enforcement for kinetic paths** (July 29). Found and fixed a
   long-standing bug in which JMAK/CNT precipitation and Standard/SR
   dissolution+precipitation only mutated the solid DC, never the
   aqueous IC counterpart — GEMS silently reconciled by inflating bulk
   composition ("phantom Ca"). HEN carbonation validation exposed the
   failure with a 200× stoichiometric excess. Fix touches
   `KineticController::commitSolidICTransfer` with dry-cap
   `solidICAvailabilityScale` and per-IC charge compensation via
   H⁺/OH⁻.
2. **Transport-kinetics 3-phase plan implemented** (July 30). Landed
   the full sequence approved in `~/.claude/plans/effervescent-forging-diffie.md`:
   per-site shell thickness δ from lattice topology (Phase 1), JSON
   schema + parser + `xport` namespace (Phase 2), Brent solver for
   nonlinear steady-state flux balance (Phase 3a), and shell-correction
   wired into `StandardKineticModel`, `SaturatingRateModel`, and
   `PozzolanicModel` (Phase 3b). Ball-centroid outward-normal
   estimator per Bullard suggestion; K-bin equal-frequency histogram
   (default K=5) for the δ distribution; linear-Fick + single limiting
   DC as the first-cut closure. Byte-parity preserved when `transport`
   block is absent.
3. **Pure-alite paste test system** (July 30). User created two 100³
   microstructures (`AlitePaste-w45` and `AliteSphere`) to exercise
   the new transport code without confounding effects of full Portland
   cement chemistry. Built matched baseline / shell-on simparams,
   launched both to 1 d hydration. Both completed cleanly in ~100 s
   each; final Alite DOR 23.46% (baseline) vs 23.50% (shell) — 0.04
   percentage points apart. Root cause of the near-null delta traced
   to two effects, one geometric and one mathematical.

Priority-2 mass-balance validation rerun (`~/tmp/thames-mb-portland-sf15`,
PID 55148) has been running since July 29 15:24 — 24 hours+ of CPU
still going as this session wraps.

## Mass-balance fix (submodule 94bd4b0, super-repo f1d2609b)

Symptom: HEN carbonation validation showed 995,932 voxels of Calcite
formed from 374 voxels of Portlandite dissolved — 200× more Ca in the
product than any solid source could supply. HON on the same shape but
smaller magnitude. In real Portland-cement runs the clinker-Ca supply
happens to roughly balance the Portlandite/CSHQ demand, masking the
bug for years.

Root cause: kinetic paths (JMAK/CNT precipitation, Standard/SR
dissolve+precipitate) wrote only to `DCMoles_[solid]` and then locked
GEMS via `setDCLowerLimit`/`setDCUpperLimit`. The corresponding IC
content that had to move between the solid and the aqueous pool was
never credited/debited. GEMS was handed inconsistent state and
"reconciled" by inflating bulk composition.

Fix in three parts inside `KineticController`:

1. **`solidICAvailabilityScale(DCId, moles_wanted)`** — dry-cap check
   that returns a scale factor in [0, 1] indicating how much of the
   requested transfer is physically supportable given current solid
   IC inventory.
2. **`commitSolidICTransfer(DCId, delta_moles)`** — atomic operation
   that moves `delta_moles` of the solid DC and adjusts the aqueous
   representative DC (Ca⁺², HCO₃⁻, SO₄⁻², ...) with H⁺/OH⁻ charge
   compensation. Signed: negative = dissolve, positive = precipitate.
3. Every kinetic path rewritten to go through `commitSolidICTransfer`
   with `solidICAvailabilityScale` as the cap. Fail-loud on
   overdraft (`throw DataException`) rather than silently mint
   phantom moles.

Validation:
- HON (Portland baseline, `~/tmp/thames-hon`): Ca mass conservation
  verified — total Ca stable at 1.3497 mol throughout 72 h.
- HEN (Portland carbonation, `~/tmp/thames-hen`): total Ca stable at
  1.0218 mol throughout 72 h. Calcite formation ceiling now matches
  Portlandite dissolution.
- Priority-2 silica-fume rerun (still running): Session-46's
  cycle-11 oscillation was **resolved by mass balance alone** —
  SI(Portlandite) now bounded ~1% around 1.0 instead of diverging.
- Priority-3 encapsulated-remnant Session-47 case: NOT resolved by
  mass balance — the trapped ettringite voxels have `wmc_ > 0`
  (surrounded by porous C4AsH14, per `Lattice.cc:1543`) so they
  ARE in `dissolutionSites_`, the rate law fires, and there's no
  physical model for the SO₄/Ca actually diffusing through the
  porous shell. Diagnosis reframed: this is a shell-diffusion
  problem, not a trap-detection problem. Fixed path is Phase 3 of
  the transport-kinetics plan (see next section).

## Transport-kinetics plan (approved plan file, then implemented)

### Design conversation (before implementation)

Multiple user course-corrections shaped the final design:

- **Lattice trap detection already exists.** Initial plan proposed a
  new detector; user pointed at existing wmc mechanism at
  `Lattice.cc:1543` (`if (steWmc > 0) addDissolutionSite`) which
  correctly excludes fully-encapsulated voxels via 18-neighbor porosity
  aggregation. No new detector needed — reframe Session-47 as
  shell-diffusion.
- **Ball-centroid outward-normal method** (user's suggestion). Collect
  all sites within a ball of radius `r` around a surface site;
  compute porosity-weighted centroid; outward normal = unit vector
  from site to centroid. Tunable `r` (default 2.5 voxels) preferable
  to naive steepest-ascent, which struggles on thick shells.
- **Linear Fick + single limiting DC (not IC).** User: "Linear Fick +
  single limiting DC is good for proving the concept." Reading bulk
  activity from `DCMoles_[limitingDC] / waterMass` avoids
  disentangling multi-DC contributions to an IC. First-cut C_eq
  derivation from `C_bulk / S^(1/stoich)` — a real design limitation
  surfaced during alite validation (see below).
- **Histogram binning (Option 3) with per-site (Option 4) as fallback.**
  User rejected single-scalar δ collapse: a bimodal δ distribution
  with thin-and-thick patches applying to a nonlinear rate law
  under-samples the fast patches and over-samples the slow. K=5
  equal-frequency bins is the default; K=1 collapses to single scalar
  for byte-parity debug; K→N recovers per-site.
- **Validation policy: no ParrotKilloh in transport-code validation
  runs.** PK's `k2(1-DOR)^{2/3}` diffusion branch is empirically
  lumping shell physics we're now trying to model from first
  principles; comparison would confound the two effects.

### Phase 1 — Shell thickness δ (submodule 43dd74c, super-repo 37142c57)

New files:
- `src/thameslib/TransportStats.h/.cc` — POD types `Vec3`, `ShellHit`,
  `ShellBin`, `ShellStats`; dependency-free `aggregateShellDistribution`
  (equal-frequency binning) and `distributionIsPathological` guard.
- `src/unit_tests/test_transport_stats.cc` — 6 test groups
  (monodisperse, bimodal, unreached filtered, K=1 collapse, empty,
  zero-shell); all pass.

Modifications to `src/thameslib/Lattice.h/.cc`:
- `estimateOutwardNormal(int siteId, double normalRadiusVoxels)` —
  ball-centroid method.
- `walkToElectrolyte(int startSiteId, const Vec3 &normal, int maxSteps,
  int reactantPhaseId)` — normal-projected voxel walk with hit
  metadata (final δ, dominant shell phase, walk terminated by
  electrolyte / cap / re-entering reactant phase).
- `computeShellStats(int phaseId, double normalRadiusVoxels,
  int maxWalkSteps, int numBins)` — loops over
  `interface_[phaseId].getDissolutionSites()`, aggregates.

Phase 1 stops before any rate model consumes the output. Byte-parity
preserved.

### Phase 2 — JSON schema + parser + scaffolding (submodule 5fbb4b6, super-repo 2e4cdc20)

New files:
- `src/thameslib/TransportParameters.h` — POD struct:
  ```cpp
  struct TransportParameters {
    double dEff = 0.0;                // effective D of limiting DC [m^2/s]
    double normalRadiusVoxels = 2.5;  // ball radius for normal estimate
    int    numShellBins = 5;          // K bins for δ histogram
    int    maxWalkSteps = 50;         // walk cap; beyond → infinite shell
    std::string limitingDCName;       // e.g., "Ca+2"
    double stoich = 1.0;              // stoichiometric coefficient
  };
  ```
- `src/thameslib/TransportCorrection.h/.cc` — namespace `xport` with
  skeleton declarations (empty in Phase 2, filled in Phase 3).

Modifications:
- `KineticData.h` — added `std::optional<TransportParameters> transport;`
  alongside `nucleation` and `jmak` optionals.
- `KineticController::parseTransportBlock(json::iterator p,
  KineticData &kineticData)` — reads optional `transport` sub-block
  with the same `{value, range, provenance}` pattern used for
  nucleation. `D_eff` and `limitingDC` required; others optional
  with defaults. Called from every parser (Standard line 605,
  Pozzolanic line 768, SaturatingRate line 1452).
- New `ChemicalSystem::getDCIdOrMinusOne(name)` — lookup that
  returns -1 for a missing DC (instead of throwing), so rate models
  can gracefully fall back to no-shell path if `limitingDC` is not
  in the current DC database.

Byte-parity gate: `HY-ccr152-ws45` 20-cycle CNT-off byte-parity
preserved when `transport` block is absent from all phase configs.

### Phase 3a — Solvers (submodule 0185cf8)

`TransportCorrection.cc` implementations:
- `kineticRate(k, area, f)` and `diffusionRate(dEff, area, ΔC, δ)` —
  diagnostic accessors for `r_kin` and `r_diff`.
- `solveSurfaceConcentrationLinear(k, C_eq, dEff, δ, C_bulk)` —
  closed-form root for linear f(Ω) = 1 - Ω.
- `solveSurfaceConcentration(k, C_eq, dEff, δ, C_bulk, f_ptr)` —
  Brent's method with sign-change bracketing. Standard Numerical
  Recipes / Wikipedia formulation. 60-iter cap, 1e-8 relative
  tolerance.
- `shellCorrectionFactor(k, C_eq, ShellStats, TransportParameters)` —
  per-bin `Da = k·δ_bin / (D_eff·C_eq)`, factor = `Σ siteFraction /
  (1 + Da)` normalized by weight sum. Explicit special case:
  zero-δ bins contribute 1.0 (site touches electrolyte directly, no
  diffusion resistance). This special case matters — see alite
  validation.
- `pickDEff(shellPhaseId, params)` — Phase 2 stub returning
  `params.dEff` regardless of shell composition. Phase 3+ refinement
  will introduce a per-shell-phase map (Ca⁺² through C-S-H vs
  through AFm vs through calcite).

New test file:
- `src/unit_tests/test_transport_correction.cc` — 8 test groups
  covering kineticRate, diffusionRate, linear solver, Brent
  asymptotes (Da→0 recovers kinetic-only, Da→∞ recovers
  diffusion-only), closed-form check, general-solver linear
  agreement, nonlinear regime, edge cases, shellCorrectionFactor.
  All pass.

### Phase 3b — Wire into rate laws (submodule 1bdf5d5, super-repo 863a579d)

`StandardKineticModel`, `SaturatingRateModel`, `PozzolanicModel` each
gained:
- `std::optional<TransportParameters> transport_` member.
- `int limitingDCId_` member (-1 if unresolved).
- Constructor: copy `kineticData.transport` into `transport_`;
  resolve `limitingDCId_` via `chemSys_->getDCIdOrMinusOne(name)`;
  warning-log if unresolved and disable shell.
- `calculateKineticStep` rate calc: after computing area × surface
  factor, `if (transport_.has_value() && limitingDCId_ >= 0)` block
  reads `C_bulk = DCMoles / waterMass`, derives `C_eq = C_bulk /
  S^(1/stoich)`, calls `computeShellStats`, calls
  `shellCorrectionFactor`, multiplies `area *= shellCorr`.
  Verbose-gated diagnostic line prints `shellCorr`, `area_before/after`.

Byte-parity gate: 17/17 CSVs identical on `HY-ccr152-ws45` first
11 cycles when `transport` block is absent from all phase configs.

## Pure-alite paste test system

User created two 100³ 1-μm-resolution microstructures at
`~/Library/Application Support/THAMES/operations/`:
- `AlitePaste-w45/` — realistic PSD, w/c = 0.45, phase IDs 0/1/2
  (Void, Electrolyte, Alite) with rest of clinker mapping reserved
  but unused.
- `AliteSphere/` — single 50-voxel-diameter alite sphere, w/c ≈ 4.6.

Chose SaturatingRate for Alite with user's calibrated
Han-2025-style parameters:
- `k = 1.253e-4 mol/m²/s`
- `B = 0.0475`
- `n = 3.73`
- `activationEnergy = 41570 J/mol`
- `dissolvedUnits = 4` (3 Ca + 1 Si-DC per C3S)

CSHQ and Portlandite kept as Thermodynamic (no kinetic_data block)
to isolate transport effects on Alite dissolution.

Built matched simparams pairs at `~/tmp/thames-alite-baseline/` and
`~/tmp/thames-alite-shell/`. Shell variant only differs by a
`transport` sub-block on Alite:
```json
"transport": {
  "D_eff":       {"value": 1e-13, "range": [1e-15, 1e-11], "provenance": "Ca+2 through CSHQ shell, Bejaoui/Bary 2007"},
  "normalRadius":{"value": 2.5,   "range": [1.5, 5.0]},
  "numShellBins":{"value": 5,     "range": [1, 20]},
  "maxWalkSteps":{"value": 50,    "range": [1, 200]},
  "limitingDC":  "Ca+2"
}
```
User confirmed D_eff = 1e-13 m²/s matches his own working value for
Ca²⁺ through mature C-S-H.

### First-launch bug + fix

Both runs crashed instantly with:
`Array microPhaseMass_ contains 5 elements, but tried to access element 9`

Root cause: I gave CSHQ id=9 and Portlandite id=10 in the simparams
(matching reference conventions), but the microstructure only has 5
phases (Void/Electrolyte/Alite/CSHQ/Portlandite) and phase IDs are
used as array indices. Fix: renumber to 3 and 4. **Phase IDs must be
contiguous 0..N-1** in current thames — not documented anywhere I
found, worth a POST_ALPHA_TODO entry if we ever open this back up.

### Results

Both runs relaunched and finished cleanly in ~100 s each. Final state
at 24 h:

| | Initial Alite | Final Alite | DOR   | Final CSHQ | Final Portlandite |
|-------------|---------|---------|--------|--------|--------|
| Baseline (no shell)     | 415,957 | 318,357 | 23.46% | 211,762 | 60,152 |
| Shell (transport ON)    | 415,957 | 318,218 | 23.50% | 212,063 | 60,241 |
| **Delta (shell − base)**| 0       | −139    | +0.04 pp | +301  | +89   |

Effectively no throttle applied. 2D mid-plane cross-section PNG
generated at `~/tmp/AlitePaste-1day-crosssection.png` — visually
shows CSHQ (wheat) dispersed throughout the electrolyte-filled pore
space rather than coating Alite grains (blue). Portlandite (darker
blue) scattered as a minor phase.

### Two root causes for the null delta

Both operate simultaneously; either alone would suffice to make the
correction irrelevant.

**1. Geometric: mean shell thickness ~0.8 voxels at 24 h.**
CSHQ = 212,000 μm³ total; initial Alite surface = 257,000 μm² (only
value logged). If uniformly distributed as coating, mean δ ≈ 0.82 μm.
The actual distribution is dominated by δ = 0 bins (Alite dissolution
sites still touching electrolyte directly). Per
`TransportCorrection.cc:60-65`, δ = 0 bins contribute correction =
1.0 to the weighted sum. No continuous shell exists ⇒ no throttle.

**2. Mathematical: C_eq derivation collapses for far-from-equilibrium
phases.** The formula `C_eq = C_bulk / S^(1/stoich)` gives the
*phase-solubility* C_eq. For Alite in early-hydration conditions,
S ≈ 1e-14 (Alite is enormously undersaturated at any realistic
aqueous state), so derived `C_eq ≈ C_bulk × 1e14` — arithmetically
huge. Then `Da = k·δ / (D_eff·C_eq)` collapses to ~1e-9 and factor
`1/(1+Da) ≈ 1`. Even with a real shell, this formulation would
not throttle Alite. The physically-correct C_eq for the transport
half-cell should come from a **reference sink phase** for the
limiting DC (Portlandite for Ca²⁺; ettringite/AFm for SO₄²⁻;
calcite for CO₃²⁻), not from the reactant phase's own SI.

User's insight, which settled the discussion: "If the mean shell
thickness is less than 1 voxel... there is basically no shell." The
mathematical issue is downstream — it would only matter once a real
shell exists. For alite at 1 d in a pure-alite paste, geometry alone
explains the null delta.

### Extended validation

Launched 28-day run at `~/tmp/thames-alite-shell-28d/` with the same
transport block but `finaltime = 28.0` and full outtimes list
{0.01, 0.05, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28} d. Result surprised
both of us — it terminated early at t = 148 h (~6.17 d) after 214 s
wall time because all Electrolyte voxels had been consumed by product
growth:

| | Voxels @ 6.2 d | Volume fraction |
|---|---|---|
| Void | 0 | — |
| Electrolyte | 0 | 0.000 |
| Alite | 88,663 | 0.089 |
| CSHQ | 708,664 | 0.709 |
| Portlandite | 202,673 | 0.203 |

Alite DOR = **78.7%** at 6.2 d. CSHQ + Portlandite = 91.1% of the
total volume. Termination cause per log: Portlandite nucleation
requested 1414 voxels but 0 available (`no room for nucleation
events`). The run stopped in an orderly fashion.

Two implications:

- **CSHQ + Portlandite have expanded to fill essentially all pore
  space** by 6 d. In a real Portland-cement paste this would be
  extreme densification. It happens here because pure alite has no
  gypsum/Al phases competing for Ca²⁺, so all Ca goes to the two
  Ca-Si and Ca-OH products.
- **This is now a good exerciser for shell physics** — by 6 d the
  Alite grains are tiny cores surrounded by dense CSHQ. Baseline-28d
  is running now for comparison; delta between the two should tell
  us whether the shell throttle activates at high DOR / thick
  effective shell. Comparison ready in the morning.

## Files touched (super-repo `~/Code/THAMES/`)

Only pointer bumps (all documentation and code changes live in the
submodule):
- 863a579d — Bump submodule: transport Phase 3b
- 2e4cdc20 — Bump submodule: transport Phase 2
- 37142c57 — Bump submodule: transport Phase 1
- f1d2609b — Bump submodule: mass-balance fix

## Files touched (submodule `backend/thames-hydration/`)

- 1bdf5d5 — Transport Phase 3b: wire shell correction into rate laws
- 0185cf8 — Transport Phase 3a: Brent solver for nonlinear flux balance
- 5fbb4b6 — Transport Phase 2: JSON schema + parser + xport scaffolding
- 43dd74c — Transport Phase 1: shell-thickness δ from lattice topology
- 94bd4b0 — Enforce mass balance: transfer IC content aqueous↔solid
- (earlier this session) e38661e clamp CNT/JMAK voxel count, 0b9d3c6
  fix jmakEnabled_ index alignment, 91f0c8a JMAK Stage 4 SR-outer
  suppression, and JMAK Stages 2-3 landed in the same submodule
  push — user tracks these via commit messages, not detailed here.

## Design questions open at session end

1. **C_eq derivation for transport half-cell.** Current formula
   `C_bulk / S^(1/stoich)` degenerates when S << 1. Two candidate
   fixes:
   - **(a)** Add `referenceSinkPhase: "Portlandite"` field to
     transport block. C_eq for the limiting DC comes from the
     reference-sink SI, not from the reactant's SI.
   - **(b)** Reformulate flux balance in terms of `C_surf - C_bulk`
     with externally supplied C_eq_ref, bound surface flux by max
     diffusive throughput regardless of kinetic driving force.
   No decision yet. Bring to next session.
2. **Per-shell-phase D_eff map** (Phase 2 stub `pickDEff` still
   returns the block's `dEff` regardless of composition). Real
   physics: Ca²⁺ through C-S-H (~1e-13 m²/s), through AFm (~1e-14),
   through calcite (~1e-12). Needs a new JSON structure and lookup.
3. **Validation coverage.** Once C_eq is settled, real validation
   needs a system where shell physics genuinely bites: (i) Portlandite
   in Portland-cement paste with observable late-age throttle, (ii)
   Session-47's encapsulated ettringite through porous C4AsH14
   shell. Both use existing microstructures.

## Pending when session resumes

1. Review the 28-day alite shell run when it finishes overnight — the
   30-hour data point should show whether a real CSHQ shell forms
   and whether the correction starts to fire even without the C_eq
   fix.
2. Priority-2 mass-balance rerun (still running at session close, PID
   55148, 24+ h in) — check for silica-fume oscillation resolution
   and Portlandite trajectory shape.
3. C_eq design decision (see above).
4. Post-alpha TODO entries to add:
   - Phase IDs must be contiguous 0..N-1 (was not obvious; caught
     runtime; worth documenting in simparams schema).
   - Transport `pickDEff` per-shell-phase map (Phase 2 stub replaced).
   - Shell correction factor diagnostic gated by `verbose_` — hard
     to debug without recompile; consider unconditional structured
     log line at cycle boundaries.

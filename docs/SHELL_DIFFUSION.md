# Shell-Diffusion Transport Correction — Reference

The shell-diffusion transport-correction framework adds a Fickian
resistance term in series with the surface-reaction rate law. It lets
the physics decide when diffusion becomes rate-limiting: as the product
shell around a reactant grain thickens, the diffusive flux through the
shell drops until it eventually caps the intrinsic dissolution rate.

    r_effective = r_kinetic_at_bulk_omega · factor(k, D_eff, δ, C_eq)

where `factor ∈ (0, 1]` is a bin-weighted average of the per-bin
correction `1 / (1 + Da)` with `Da = k · δ_bin / (D_eff · C_eq)`.

**Why it exists.** There is a long-standing and unresolved
controversy in cement science about when diffusion-controlled kinetics
takes over during hydration. One camp locates the transition at or
before the main heat-flow peak (12 h or less); another attributes the
peak to space-filling of hydration products and puts the onset days
later. THAMES stays neutral by design: the framework is available for
any phase that opts in, throttling emerges naturally as shells thicken,
and no time-based onset is hand-coded anywhere. See
`~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/project_transport_kinetics_science_position.md`
for the position in full.

**Which phases should use it:** any phase whose intrinsic surface-
reaction rate is fast enough that diffusion through a growing product
shell can plausibly become rate-limiting at some point in hydration.
Alite is the natural first target (C-S-H shell around C3S is the
canonical shell-diffusion setup in the cement-kinetics literature).
Off by default for every production phase in the current release —
enabling for a specific phase is a science-review decision that
requires reasonable calibration of `dEff` for that reactant / shell
pair.

## 1. File responsibilities

| File | Role |
|---|---|
| `src/thameslib/TransportStats.h/.cc` | Pure-math POD types + `aggregateShellDistribution` free function in `namespace xport` — no THAMES deps. Turns a raw per-site δ distribution into a K-bin equal-frequency histogram. Unit-tested standalone (`test_transport_stats`). |
| `src/thameslib/TransportParameters.h` | POD struct holding `{dEff, normalRadiusVoxels, numShellBins, maxWalkSteps, limitingDCName, stoich}` for one phase's opt-in transport block. |
| `src/thameslib/TransportCorrection.h/.cc` | Pure-math free functions in `namespace xport` — `shellCorrectionFactor` (production path, linear-rate closed form summed per bin), `solveSurfaceConcentration` (Brent iteration on an arbitrary driving-force functor — implemented and unit-tested but not yet called by any kinetic model), `pickDEff` (currently a global-`dEff` stub; per-shell-phase map is deferred). Unit-tested standalone (`test_transport_correction`). |
| `src/thameslib/KineticData.h` | Adds `std::optional<TransportParameters> transport` — parse-time carrier. |
| `src/thameslib/KineticController.h/.cc` | Adds `parseTransportBlock` and calls it from `parseKineticDataForStandard / -Pozzolanic / -SaturatingRate` after `parseNucleationBlock`. Also carries a verbose-gated per-cycle shell-thickness histogram diagnostic that is independent of the production consumption path. |
| `src/thameslib/Lattice.h/.cc` | Adds `estimateOutwardNormal` (ball-centroid outward-normal method), `walkToElectrolyte` (step-limited walk through product-phase voxels), and `computeShellStats` (aggregates one phase's per-site δ into the K-bin histogram). |
| `src/thameslib/{StandardKineticModel, SaturatingRateModel, PozzolanicModel}.{h,cc}` | Each carries a `std::optional<TransportParameters> transport_` member and a `limitingDCId_`. Each `calculateKineticStep` multiplies `area` by `shellCorrectionFactor(...)` when the transport block is present and the limiting DC resolved to a valid id. Standard's call-site block comment carries the full derivation; SR and Pozz point at it. |
| `src/unit_tests/{test_transport_stats,test_transport_correction}` + build harnesses | Standalone regression tests. |

## 2. JSON schema

```json
"kinetic_data": {
  "type": "SaturatingRate",
  "rateConstant": 1.253e-4,
  "dissolution": { ... },
  "transport": {
    "dEff": 1.0e-13,
    "normalRadiusVoxels": 2.5,
    "numShellBins": 5,
    "maxWalkSteps": 50,
    "limitingDCName": "Ca+2",
    "stoich": 3.0
  }
}
```

**All fields are scalar** — no `{value, range, provenance}` wrapping.
This is deliberately different from the CNT `nucleation` block: shell-
diffusion parameters are physical measurements (D_eff has literature
values for common shell compositions) or geometric knobs (K, walk cap),
not knobs to sweep. If a paper publishes a new D_eff for Ca²⁺ through
C-S-H, edit the JSON. The CNT block's provenance metadata exists
because γ and A₀ are jointly degenerate and users sweep them; that's
not the case here.

**Absence of the `transport` block is the default.** When the block
is absent, `KineticData::transport` stays empty, the kinetic model
sees `transport_.has_value() == false`, and `area *= shellCorr` is
skipped. Backwards-compatible with every existing config.

**Field notes:**

| Field | Default | Notes |
|---|---|---|
| `dEff` | 0.0 (must supply) | Effective diffusivity of the limiting DC through the shell, m²/s. Literature order: Ca²⁺ through C-S-H ~1e-13; SO₄²⁻ through AFm ~1e-14; Ca²⁺ through calcite shell ~1e-12. Users calibrate. |
| `normalRadiusVoxels` | 2.5 | Radius of the ball used to estimate the outward normal at each surface site (Bullard's centroid method). Voxel units. Too small collapses to nearest-neighbor and is noisy; too large lets non-local topography bias the direction. |
| `numShellBins` | 5 | K, the number of equal-frequency bins in the per-phase δ histogram. K=1 collapses to a single scalar (debugging / byte-parity); K → N_sites approaches per-site rate summation. |
| `maxWalkSteps` | 50 | Cap on the outward walk through product voxels. Sites whose walk exceeds this without reaching electrolyte are treated as δ → ∞ (contribute zero flux) and dropped from the aggregate — the fraction thus dropped is logged. |
| `limitingDCName` | `""` (disabled) | Name of the DC whose diffusion through the shell rate-limits the reaction. **DC name, not IC name** — `Ca+2` for Alite / Belite / Portlandite, `SO4-2` for ettringite / gypsum, `SiO2@` for silica fume. Empty string = transport block parsed but disabled. |
| `stoich` | 1.0 | Stoichiometric coefficient of the limiting DC in the solid's dissolution reaction. 1 for Ca in Portlandite; 3 for Ca in C3S; 6 for Ca in ettringite; 3 for SO₄ in ettringite. Used to invert bulk SI back to C_eq (see §3). |

## 3. Derivation

Steady-state flux balance at a reactant surface with a product shell
of thickness δ, for the linear rate law `r = k · (1 − C_surf/C_eq)`
(dissolution):

    k · (1 − C_surf / C_eq)  =  D_eff · (C_surf − C_bulk) / δ

Solve for `C_surf` and substitute back into `r`, then divide by the
no-shell rate `r_bulk = k · (1 − C_bulk/C_eq)`:

    factor  =  r_shell / r_bulk  =  1 / (1 + Da)
    Da      =  k · δ / (D_eff · C_eq)

`shellCorrectionFactor` sums that per-bin, weighted by `siteFraction`
in each bin of the K-bin δ histogram. For the linear rate this is
EXACT. For nonlinear f (Standard's `(1 − Ω^p)^q`, SR's saturating
form), it is a first-order approximation that is exact near
equilibrium and degrades gracefully far from equilibrium.

**Limits.**

- **`Da → 0`** (thin shell, large D_eff, or fast supply):
  `factor → 1` — no throttle, intrinsic rate dominates. As δ → 0 the
  bin contributes exactly 1 to the sum (no-op).
- **`Da → ∞`** (thick shell, small D_eff): `factor → 0` — diffusion
  fully rate-limits; `C_surf → C_eq` and the intrinsic rate at the
  surface collapses.
- **`C_bulk → C_eq`** (near-equilibrium): rate is small regardless
  of shell; `factor` stays well-behaved.

## 4. C_eq / K-correction dependency (critical for cold readers)

The kinetic models derive C_eq at the call site from the reactant's
own saturation index:

    C_eq = C_bulk / SI^(1/stoich)

with `SI = (C_bulk / C_eq)^stoich` assuming dilute-solution behavior
(activity ≈ concentration) and single-species-dominant contribution
to the ion-activity product. Both approximations are fine for typical
Portland pore solutions and worth revisiting at high ionic strength.

**The numeric magnitude of C_eq is only physically sensible when the
phase's equilibrium constant is itself physical.** Sessions 56 and 57
corrected `ln K(C3S)` and `ln K(C3A)` to reconcile the Babushkin-
heritage CemData18 values with experimentally-measured dissolution
equilibria (Nicoleau/Bullard 2015 for C3S, Ye et al. 2022 for C3A).
Before those corrections, `S(Alite)` in a real paste was ~1e−14 and
the derived `C_eq` came out ~1e14 mol/m³ — an artifact, not a
formulation error, and one that made the shell throttle indistinguishable
from zero regardless of δ.

**Post-correction sanity check.** Pure C3S in pure water reaching
equilibrium via `K = [Ca²⁺]³ · [H₄SiO₄] · [OH⁻]⁶ = exp(−50.7)`:

    x = (K / (27 · 46656))^(1/10) ≈ 1.54 mM   (extent of reaction)
    [Ca²⁺] ≈ 4.6 mM,  [H₄SiO₄] ≈ 1.5 mM,  [OH⁻] ≈ 9.2 mM  (pH ≈ 12)

In a real Portland paste with `C_bulk[Ca²⁺] ≈ 20 mM` buffered by
Portlandite and `S(Alite) ≈ 1e−3` post-K-fix, `C_eq(Alite, Ca) ≈ 200
mM`. Critical shell thickness `δ_critical = D_eff · C_eq / k` with
`D_eff = 1e−13 m²/s`, `k = 1e−7 mol/m²/s` comes out `≈ 200 μm` —
reachable in late-age cement paste, so the current formulation should
throttle in that regime.

**Any future clinker phase moving from PK to SR / Standard needs the
same K audit before its transport block will behave sensibly.**
`docs/POST_ALPHA_TODOS.md` carries the standing action item.

## 5. What's landed vs deferred

**Landed** (Session 55, submodule commits `43dd74c` / `5fbb4b6` /
`0185cf8` / `1bdf5d5`):

- Per-site δ estimation via `Lattice::estimateOutwardNormal` +
  `walkToElectrolyte` (ball-centroid outward-normal method).
- K-bin equal-frequency histogram aggregator (`aggregateShellDistribution`).
- Linear-rate closed-form shell correction (`shellCorrectionFactor`).
- Brent-iteration nonlinear solver (`solveSurfaceConcentration`) —
  implemented and unit-tested; not currently called.
- Per-phase parser (`KineticController::parseTransportBlock`) with
  fail-loud validation.
- Wired into Standard, SaturatingRate, and Pozzolanic
  `calculateKineticStep` — opt-in per phase via the `transport` block.
- Byte-parity preserved on CNT-off `HY-ccr152-ws45` — dispatch is
  inert unless the phase declares a transport block.

**Deferred / not yet done** (tracked in `docs/POST_ALPHA_TODOS.md`
under "Shell-diffusion long-duration validation run" and its
"Refinements that may be worth landing first" list):

- Wire `solveSurfaceConcentration` at the call sites so SR / Standard /
  Pozzolanic get the true-nonlinear shell correction instead of the
  linear-rate closed form. Would tighten the throttle near equilibrium.
- Per-shell-phase D_eff map in `pickDEff` — the loop in
  `shellCorrectionFactor` already passes `bin.dominantShellPhaseId`
  through, so the only remaining piece is a real config-driven map.
- Runtime selection of the limiting DC when a phase has multiple
  candidates (currently pinned per-phase in config).
- Long-duration validation run: watch emergent throttling grow with
  shell thickness through hydration on a realistic microstructure to
  28 d — 90 d. The empirical anchor needed before defensibly enabling
  transport for a production phase.

## 6. Verification

- `src/unit_tests/test_transport_stats` — 6 groups covering the walk,
  the normal-vector estimate, the K-bin aggregator, and the
  distributionIsPathological detector.
- `src/unit_tests/test_transport_correction` — 8 groups covering
  the linear closed form, the Brent solver, `pickDEff`, and
  `shellCorrectionFactor` at Da → 0 / Da → ∞ / near-equilibrium
  limits.
- **Byte-parity on CNT-off `HY-ccr152-ws45`** (Session 55) —
  17/17 CSVs identical to pre-transport-plumbing baseline through
  11 cycles when no phase declares a `transport` block.
- **Pure-alite paste short-time throttle** (Session 57,
  post-K-correction) — SaturatingRate Alite with
  `transport: { dEff: 1e-13, limitingDCName: "Ca+2", stoich: 3 }`
  gave 40% relative rate reduction at 24 h vs baseline. Empirical
  proof the throttle activates once C_eq is physical. Direction
  and magnitude both physically sensible.
- **Long-duration validation run:** pending — see the POST_ALPHA
  entry. The current 6-day electrolyte-exhaustion in the S55
  pure-alite runs is a known limit that a realistic Portland paste
  at higher resolution and w/c should avoid.

## 7. References

- G. Damköhler, *"Einfluß von Diffusion, Strömung und Wärmeübergang
  auf die Ausbeute bei chemisch-technischen Reaktionen"*, Zeitschrift
  für Elektrochemie und angewandte physikalische Chemie **42** (1936)
  846–862. Original introduction of the four Damköhler numbers.
- O. Levenspiel, *Chemical Reaction Engineering* (3rd ed., Wiley,
  1999), Chapter 25 (Fluid-Particle Reactions) — shrinking-core and
  shell-diffusion models.
- C.I. Steefel, A.C. Lasaga, *"A coupled model for transport of
  multiple chemical species and kinetic precipitation/dissolution
  reactions with application to reactive flow in single phase
  hydrothermal systems"*, American Journal of Science **294** (1994)
  529–592.
- P.C. Lichtner, *Continuum Formulation of Multicomponent-
  Multiphase Reactive Transport*, in *Reactive Transport in Porous
  Media*, Reviews in Mineralogy Vol. 34, MSA (1996) — Damköhler /
  Péclet regime analysis.
- J.W. Bullard, *"Approximate rate constants for nonideal diffusion
  in complex reaction-diffusion systems"*, Journal of Physical
  Chemistry A **111** (2007) 2084–2092.
- L. Nicoleau, A. Nonat, *"A new view on the kinetics of tricalcium
  silicate hydration"*, Cement and Concrete Research **86** (2016)
  1–11. Reaction-diffusion coupling context in cement paste.

**Related THAMES documents.**

- `docs/transport_kinetics_brainstorm.md` — verbatim record of the
  design conversation from Session 49.
- `docs/SATURATING_RATE.md` — companion kinetic-law reference.
- `docs/CNT_ARCHITECTURE.md` — companion CNT nucleation reference.

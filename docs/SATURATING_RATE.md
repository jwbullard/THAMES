# SaturatingRateModel — Reference

`SaturatingRateModel` is the fourth concrete `KineticModel` subclass in
THAMES's C++ hydration engine, joining `ParrotKillohModel`,
`StandardKineticModel`, and `PozzolanicModel`. It implements the
saturating rate law of Bullard 2015 CCR Eq. (2) / Han 2025 CEJ Eq. (7):

    r_diss(Ω<1) = k · (1 − exp[−(−B ln Ω)^n])
    r_prec(Ω>1) = k · (1 − exp[−( B ln Ω)^n])

**Why a new class:** `StandardKineticModel` uses the power-law form
`r = k (1 − Ω^m)^n` (Han 2025 Eq. 6) which diverges at extreme Ω. That
divergence caused the Step-6 dt-collapse pathology when Portlandite was
CNT-nucleated in a Portland cement paste — same growth rate that
couldn't consume Ca fast enough at moderate S ballooned into 2.8 M-voxel
single-cycle requests once the rate constant was raised. The saturating
form saturates at `k` in the far-from-equilibrium limit, capturing the
etch-pit → step-flow mechanism transition.

**Which phases should use it:** any phase with published Han-style
dissolution calibration. Portlandite is the first target (Han et al.
2025 CEJ); Alite is a natural second (also validated by Bullard);
others as literature accumulates.

## 1. File responsibilities

| File | Role |
|---|---|
| `src/thameslib/SaturatingRate.h/.cc` | Pure-math free functions in `namespace sat` — no state, no `this`, no external deps beyond `<cmath>`. Unit-tested standalone. |
| `src/thameslib/SaturatingRateParameters.h` | POD struct holding `{rateConstant, B, n}` for one direction (dissolution or precipitation) |
| `src/thameslib/SaturatingRateModel.h/.cc` | KineticModel subclass — pulls parameters from KineticData at construction, wraps `sat::` calls with surface-area, RH, Arrhenius, dissolvedUnits scaling, and the same keepDCLowerLimit / mass-conservation bookkeeping as `StandardKineticModel`. Carries the four CNT virtuals symmetric with Standard/Pozzolanic. |
| `src/thameslib/KineticData.h` | Adds `std::optional<SaturatingRateParameters> saturatingDissolution / saturatingPrecipitation` — parse-time carriers |
| `src/thameslib/KineticController.h/.cc` | Adds `parseKineticDataForSaturatingRate` + `parseSaturatingRateSubBlock` parser helpers; SaturatingRateType branch in dispatcher and in `makeModel` |
| `src/thameslib/global.h` | Adds `SaturatingRateType = "SaturatingRate"` string constant |
| `src/unit_tests/test_saturating_rate.cc` + `build_and_run.sh` | Standalone regression test — Han 2025 Fig. 5 Portlandite rates plus boundary and Arrhenius checks |

## 2. JSON schema

```json
"kinetic_data": {
  "type": "SaturatingRate",
  "surfaceAreaMultiplier": 1.0,
  "dissolvedUnits": 3,
  "activationEnergy": 13900.0,
  "dissolution": {
    "rateConstant": 4.05e-4,
    "B": 0.74,
    "n": 1.9
  },
  "precipitation": {
    "rateConstant": 4.05e-4,
    "B": 0.74,
    "n": 1.9
  },
  "nucleation": { ... optional CNT block, same schema as Standard ... }
}
```

**Scalar fields** — plain values, no `{value, range, provenance}`
wrapping. This is deliberately different from the CNT `nucleation`
block: the saturating-rate parameters are a **calibrated fit** from a
published paper, not a knob for what-if exploration. If a paper publishes
new parameters, edit the JSON. The CNT block's provenance / range
metadata exists because CNT γ and A₀ are jointly degenerate and users
routinely sweep them; that's not the case here.

**`dissolution` is required** for a SaturatingRate-type phase.
`KineticController::parseKineticDataForSaturatingRate` throws a
`DataException` if it is missing.

**`precipitation` is optional.** Han et al. 2025 measured only
dissolution (Ω < 1); near equilibrium the precipitation rate follows
by microscopic reversibility, but far from equilibrium the two branches
can differ. If the `precipitation` block is absent, `SaturatingRateModel`
uses the dissolution parameters as a symmetric working default and logs
one line per phase noting the fallback (via the
`precipitationFallbackLogged_` per-instance latch — one line per phase,
per run).

**`nucleation` is optional** — the CNT block schema is unchanged from
Standard/Pozzolanic; see `docs/CNT_ARCHITECTURE.md` §2.

## 3. Han/Bullard equivalence

Bullard 2015 CCR Eq. (2), original notation for alite dissolution:

    r = k_C3S · A_eff · (1 − exp[−((ln K − ln Q) / C₁)^r_exp])

Han et al. 2025 CEJ Eq. (7), calcium-hydroxide dissolution:

    r = k · (1 − exp[−(−B ln Ω)^n])

The two forms are algebraically equivalent under:

| Han | Bullard | Notes |
|---|---|---|
| `k`     | `k_C3S`  | surface-normalized rate constant |
| `B`     | `1/C₁`   | inverse driving-force scaling |
| `n`     | `r_exp`  | exponent |
| `Ω`     | `Q/K`    | reaction quotient / equilibrium constant |
| — | `A_eff` outer factor | subsumed into `SaturatingRateModel`'s surface-area handling; both models multiply through by `area × surfaceAreaMultiplier` |

`SaturatingRateModel` uses Han's `B/n` naming because Han 2025 is the
current published Portlandite calibration and drives the first physics
validation.

## 4. Portlandite calibration (Han et al. 2025 at 24 °C)

| parameter | value | units | source |
|---|---|---|---|
| `rateConstant` | 4.05 × 10⁻⁴ | mol m⁻² s⁻¹ | Han 2025 CEJ Table 3 |
| `B`            | 0.74        | dimensionless | Han 2025 CEJ Table 3 |
| `n`            | 1.9         | dimensionless | Han 2025 CEJ Table 3 |
| `activationEnergy` | 13,900  | J/mol | Han 2025 CEJ Table 3 |
| `dissolvedUnits` | 3         | — | stoichiometry Ca(OH)₂ → Ca²⁺ + 2 OH⁻ |

Reference: `~/Documents/Papers/Han/Han-2025-Calcium-hydroxide-di.pdf`.

## 5. CNT interaction

When a SaturatingRate phase carries a `nucleation` block:

- **Zero-mass bypass** — mirror of `StandardKineticModel.cc:195`: if
  `nucleation_.has_value() && scaledMass <= 0.0`, `calculateKineticStep`
  returns immediately with `massDissolved = 0`. This ensures CNT is the
  sole entry point for the phase (SaturatingRate's `area = 1.0` fallback
  cannot spontaneously precipitate through the mass-balance route).
- **The four CNT virtuals** (`computeNucleationVoxels`, `hasNucleation`,
  `accumulateNucleation`, `drainNucleationInteger`) are byte-symmetric
  with `StandardKineticModel`'s versions. Anything CNT knows how to do
  with a Standard-model phase, it now does identically with a
  SaturatingRate phase.

See `docs/CNT_ARCHITECTURE.md` for the CNT cycle-by-cycle flow.

## 6. Verification

- `src/unit_tests/test_saturating_rate` — Han 2025 Fig. 5 Portlandite
  rates at Ω = 0.05, 0.1, 0.3, 0.5, 0.7, 0.9 plus dissolution boundary
  conditions, precipitation-branch checks, and Arrhenius scaling. Exit
  0 on all-pass.
- **Byte-parity on CNT-off `HY-ccr152-ws45`** — dispatch is inert
  unless a phase declares `"type": "SaturatingRate"`, so the addition
  of the class must not perturb any existing config. Validated 17/17
  CSVs identical through 11 cycles at S1, S2, and S3 (see
  `~/tmp/thames-satrate-s2/`).
- **Portlandite physics validation** — `~/tmp/thames-satrate-val/`:
  configs 4a (SaturatingRate, no CNT) and 4b (SaturatingRate + CNT)
  vs archived Step-6 6b (Standard + CNT that stalled). Summary in
  `~/tmp/thames-satrate-val/saturating_rate_validation.md`. Key result:
  4a cleared 6b's dt-collapse cleanly; 4b cleared 6b's stall point but
  hit a separate CNT ↔ GEMS mass-balance throttle documented in
  `POST_ALPHA_TODOS.md`.

## 7. References

- J.W. Bullard, G.W. Scherer, J.J. Thomas, *Time dependent driving
  forces and the kinetics of tricalcium silicate hydration*, Cement and
  Concrete Research, 74 (2015) 26–34.
- Y. Han, M.G. Ucak-Astarlioglu, J.F. Burroughs, J.W. Bullard, *Calcium
  hydroxide dissolution rates: Dependence on temperature and
  saturation*, Chemical Engineering Journal, 515 (2025) 162484.

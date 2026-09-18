# Sessions 68–69 Summary (Sep 18, 2026): self-desiccation — RH→rate coupling restored, volume-accounting blocker found

## Context

S68 reprioritized the science queue: **self-desiccation first** (the sponsor wants the partitioning of pore solution among pores down to the nm scale), **isothermal-calorimetry enthalpy second**. S68 surveyed the C++ and paused for a Ghostty Full Disk Access restart before reading the reference papers. S69 resumed.

## Literature read (copies in `~/tmp/thames-desiccation-refs/`)

- **Parrott & Killoh 1984**, Brit. Ceram. Proc. 35:41–53. Confirms f(rh) = [(rh − 0.55)/0.45]⁴ (p. 48, Fig. 6): a loose empirical fit to overall Portland-cement rate vs RH (Powers 1947, Copeland & Bragg 1955, Mills 1965, Parrott 1973), applied to all four clinker phases because no per-compound data existed. The 0.55 is a fit parameter.
- **Patel, Killoh, Parrott & Gutteridge 1988**, Mater. Struct. 21:192–197. OPC w/c 0.59, 2 d saturated then fixed RH. QXRD hydration gain 14→90 d relative to saturated: 0.38 / 0.60 / 0.93 at 81 / 91 / 97 % RH, ~0 at ≤ 69 %. Linear with h0 = 0.70 fits (0.37 / 0.70 / 0.90); PK-1984 underestimates ~3× at 81 %. Per-mineral curves: belite steeper, C3A/C4AF gentler. Drying-induced collapse moves small-pore (< 37 nm) volume into large pores (> 37 nm); it is time-dependent; < 4 nm loss evident below ~95 % RH; surface-area loss below ~60 %.
- **Killoh, Parrott & Patel 1989**, ACI SP-114-7. OPC/fly ash 70/30: bound water flat below ~70 % RH, ~linear above; pozzolanic reaction restricted below 80 %; OPC large-pore gain 14→90 d ≈ +0.03–0.04 below 70 % RH (~20 % of small porosity).

## Code findings (correcting S68)

- There was **no live RH throttle in any kinetic model**. The Kelvin RH was computed only in model constructors, on an empty pore-size distribution, so `getLargestSaturatedPore` returned its 1000 nm default and rhFactor was constant for the whole run (0.98 PK, 0.998 otherwise). The per-step recompute was removed in submodule `85f55e6` (Jul 2024).
- `getLargestSaturatedPore` tested `volfrac` instead of `volfracsat`.
- `calcMasterPoreSizeDist` read a row before checking the row bound.

## Landed (submodule `0575a60`, super-repo `fc9794dd`)

Applied as six supervised steps, each built before the next:

1. `getLargestSaturatedPore`: tests `volfracsat`, skips empty bins, returns −1 when every pore is saturated.
2. `calcMasterPoreSizeDist`: bound check before row read.
3. New `HumidityParameters.h` — f(h) = [max(0, (h − h0)/(1 − h0))]ⁿ, defaults **h0 = 0.70, n = 1** (Jeff's decision, from Patel 1988 / Killoh 1989), PK-1984 documented as alternative. `rh_`, `rhFactor_`, `humidity_`, and `setRelativeHumidity()` moved to the `KineticModel` base; seven constructor Kelvin blocks, the 0.551 floor, and orphaned comment blocks deleted.
4. `KineticController::updateRelativeHumidity()` runs at the start of each fresh (non-retry) step: RH = 1 exactly in saturated mode; in sealed mode the pore distribution is recomputed and the Kelvin RH pushed to every model.
5. Optional per-phase `rh_dependence` block `{h0, exponent}` in `kinetic_data` (`{value, range, provenance}` pattern), parsed once for all model types; reset between phases in `initKineticData`.
6. `Lattice::getKelvinRH()` / `getInternalRH()` and `ChemicalSystem::getWaterActivity()`; PoreSizeDistribution CSVs gain `Kelvin relative humidity`, `Water activity`, `Internal relative humidity` lines. **Rates use Kelvin RH only** (so saturated curing gives f = 1, matching the calibration data); internal RH = a_w × Kelvin is reported and will drive gel collapse.

Behavior change: saturated runs now use rhFactor = 1 exactly (+1.9 % rate for PK phases, +0.2 % otherwise vs before).

Also filed in POST_ALPHA: make pore-solution surface tension γ a simulation parameter (inorganic pore solution *raises* γ ~1 mN/m — negligible; shrinkage-reducing admixtures lower it sharply).

## Validation (`~/tmp/thames-rh-validation/`, cem151-neat, w/c 0.44, 28 d)

- New binary, saturated and sealed: both exit 0 in ~8.5 min. Water activity from GEMS is mole-fraction scale, 0.998 → 0.978 over 28 d. Saturated DOR at 72 h 0.5387 (new) vs 0.5357 (old).
- **Blocker: sealed mode never desaturates — in old and new binaries.** Empty pore volume is 0 at every output, Kelvin RH stays 1, and sealed ≡ saturated. Every cycle `Lattice::adjustMicrostructureVolumes` finds more water than non-solid volume and trims the excess. Phase volumes at 28 d sum to 8.85e-5 vs initial 7.55e-5 (+17 % growth instead of ~−7 % chemical shrinkage). One confirmed contributor: `ChemicalSystem::calculateState` inflates solid volumes by 1/(1 − φ) (CSHQ φ = 0.26) while the electrolyte volume is the full GEMS aqueous volume, so gel water is counted twice (~half the excess). The remaining ~+8 % is unexplained.
- Old binary was ~3× slower per cycle (~3 GEMS solves/cycle vs ~1.2); cause unidentified. Old runs killed at 552 h (saturated) and 77 h (sealed, apparently stalled).

## Deferred

- **Volume accounting** — next session's entry point; full handoff in memory `project_volume_accounting_handoff.md` (evidence, suspects in order, questions for Jeff).
- **Step 8, gel-pore collapse** — designed, not started: when internal RH < 0.95, a collapsed CSHQ fraction χ relaxes toward χ_max ≈ 0.20 with time constant τ (placeholder ~30 d), moving CSHQ pore volume from < 37 nm into its own 37–99 nm bins at constant internal porosity; newly formed CSHQ after RH recovers is uncollapsed. Pointless until sealed mode can desaturate.
- Continuous RH-vs-time output (currently only at output times) — decide after sealed mode works.
- Calorimetry enthalpy work — queued behind self-desiccation.

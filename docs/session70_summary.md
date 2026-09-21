# Session 70 Summary (Sep 20, 2026): water created from nothing in the kinetic IC transfer — fixed; sealed mode now self-desiccates

## Context

S69 ended with a blocker: in sealed mode no pore ever emptied, because THAMES's phase volumes grew ~17 % over 28 d instead of showing ~7–8 % chemical shrinkage. The handoff memory listed suspects and three design questions for Jeff. All water-distribution work was escalated to **high priority** this session (sponsor needs accurate water distribution now).

## Jeff's answers to the three design questions

1. **Gel-pore water:** option (a) — CSHQ voxels carry their gel water; Electrolyte is capillary-scale solution. Turned out to be **already implemented**: `Lattice::adjustMicrostructureVolumes` compares dense solid (`solidVolumeWithPores_ − subvoxelPoreVolume_`) plus total water against the fixed initial volume and fills sub-voxel pores first.
2. **Fixed microstructure volume:** keep it. Discussion: correct physics after set (the skeleton resists; autogenous bulk strain ~0.01–0.1 % vs ~7 % chemical shrinkage); before set a fluid paste consolidates instead of forming voids (~0.3–0.7 % paste-volume error, kinetically harmless, biases early porosity/images). Autogenous strain could later be computed poromechanically from saturation + Kelvin capillary pressure.
3. **Where chemical-shrinkage emptiness goes:** empty the largest pores first by converting Electrolyte → VOID, ideally as clustered, roughly spherical cavities.

## Root cause (not a kinetic-model bug)

`KineticController::commitSolidICTransfer` (introduced by the S55 mass-balance fix, `94bd4b0`) moves each element of a dissolving/precipitating kinetic solid into solution as one fixed stand-in ion (Ca→Ca⁺², Si→SiO₂@, Al→Al⁺³, …) and balances charge with OH⁻/H⁺, but **never balances O or H**. GEMS3K derives the bulk composition from THAMES's DC amounts, so those atoms become real. C₃S + 3 H₂O → 3 Ca²⁺ + 6 OH⁻ + SiO₂ was written without removing the 3 H₂O: +3 H₂O per C₃S, +2 per C₂S, +6 per C₃A, +2 per kinetic Portlandite precipitated. On cem151-neat (w/c 0.44, 28 d) total H rose 4.936 → 7.024 mol and O 4.687 → 5.708 (≈1.04 mol H₂O injected ≈ 1.88e-5 m³ per 100 g) while Ca and Si were conserved. Removing it turns the +17 % "growth" into −7.7 % — the expected chemical shrinkage. The S69 "gel water counted twice" suspicion was retracted: `PhaseVolumes.csv` reports raw GEMS volumes, so it never included the 1/(1−φ) inflation.

## Landed (submodule `0343374`, super-repo `26069888`)

- **Step A:** after the mapped transfers and charge compensation, accumulate the net O and H change (solid + mapped aqueous DCs + OH⁻/H⁺) and add/remove exactly that much H₂O@ so O is conserved; warn if H is then unbalanced (redox mismatch) or if H₂O@ would go negative.
- **Step A2:** Fe maps to **Fe⁺³** instead of Fe⁺² in both `icNameToAqDCName` and `ChemicalSystem::checkICMoles` (kept in sync). Iron in C₄AF and Fe hydrates is Fe(III); the Fe⁺² mapping left 2 H per C₄AF unbalanced (1161 warnings) and destabilized ettr-AlFe enough that a step-A-only saturated run stalled at the 1e-5 h timestep floor at 76.6 h (encapsulated C4AsH14 recall loop — the known near-depletion failure).

## Validation (`~/tmp/thames-rh-validation/`, cem151-neat, 28 d; comparison script `compare_rh.py`)

| | sealed, pre-fix | sealed, A+A2 | saturated, pre-fix | saturated, A+A2 |
|---|---|---|---|---|
| H (mol) 0→28 d | 4.936 → 7.024 | 4.936 → **4.936** | 4.936 → 7.035 | 4.936 → 5.624 |
| O (mol) 0→28 d | 4.687 → 5.708 | 4.687 → **4.687** | 4.687 → 5.713 | 4.687 → 5.031 |
| DOR at 28 d | 0.7967 | 0.7938 | 0.7967 | 0.7967 |
| Kelvin RH / a_w / internal RH at 28 d | 1 / 0.978 / 0.978 | 0.971 / 0.953 / **0.925** | — | — |

- Sealed: VOID appears immediately (0.16 % at 15 min, ~7 % by 14 d); the meniscus recedes into gel pores after the capillary Electrolyte is gone (~400 h); internal RH 0.925 at 28 d is in the range typically measured for sealed w/c 0.44 pastes. Dissolved salts contribute about as much of the RH drop as the menisci.
- Saturated: completes 28 d, DOR unchanged; external water uptake 0.344 mol ≈ 0.062 mL/g cement at α ≈ 0.8 — textbook chemical-shrinkage imbibition.
- Ca11mM smoke test: unchanged (only 1.4e-4 mol alite dissolves in 1 h).

## Problems found, not yet fixed

- **VOID ignored by the pore-size distribution** (VOID internal porosity hard-coded 0 at `ChemicalSystem.cc:627-629`): the CSV reports zero empty capillary porosity and Kelvin RH reads exactly 1 while voids exist. **Step B proposal is in the handoff memory** — local change in `Lattice::getPoreVolumeFractions` only, because the same zero drives the wetted-surface (`wmc`) weights for kinetics.
- **Late-age products placed in VOID voxels:** once Electrolyte voxels reach 0 (~400 h sealed), `Lattice::nucleatePhaseRnd` (~line 2083) falls back to VOID sites, so the void fraction falls (0.072 → 0.034 by 28 d) while the gel pores empty. Idea: densify CSHQ (lower its internal porosity) instead.
- **Stale provenance hash** from plain `make` in `build/`: `version.h` is only regenerated when CMake is reconfigured; re-run `cmake ..` before validation builds.

## Decisions and design notes for upcoming work

- **Capillary depercolation:** Jeff clarified gel/interhydrate pores are always percolated, so depercolation lowers the water-supply *rate* rather than stopping it. Decision: once capillary pores depercolate, treat the microstructure as **sealed** even if the user selected saturated curing (the zero-supply limit; a depth + permeability + suction supply model stays a possible refinement).
- **Connectivity schedule:** solids + electrolyte connectivity every 10 min of hydration time until initial set; capillary-pore connectivity every 1–2 h after set; never every cycle.
- **Port VCCTL `burnset` / `burn3d`** (`~/Code/VcctlGtk/backend/src/include/`), modernized for C++ with better documentation. Notes: `burnset` needs per-voxel particle IDs (the `.pimg` image, not currently loaded by the THAMES backend); VCCTL's set flag is a 0.985 connected fraction (initial-set threshold is Jeff's call); plan a single connected-component labeling pass with per-direction non-periodic face-spanning tests (S64 lesson), flat `std::vector` labels, phase classes from THAMES names.
- **IC-transfer oxidation states:** the element→ion table is element-keyed but fixes one oxidation state per element. Correct for all current kinetic solids; wrong for any kinetic sulfide, Fe(II)/Fe(0), graphite, or nitrate/nitrite phase (e.g. kinetic pyrrhotite oxidation, which would also need an O₂ supply term). Filed in POST_ALPHA as needed soon. Sulfides are fine today as equilibrium phases.

## Queue (all high priority)

B (VOID in pore-size distribution) → C (clustered spherical cavities via Euclidean distance transform + adjacency growth) → D (`burnset`/`burn3d` port, set detection, depercolation switch) → E (late-age product placement) → pre-set shrinkage → gel-pore collapse → Kelvin adsorbed-film correction → continuous RH/saturation time series. Entry point: memory `project_volume_accounting_handoff.md`.

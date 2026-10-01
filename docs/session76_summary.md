# Session 76 (Oct 1, 2026): the w/c 0.32 run, meniscus reporting fixes, C-S-H gel outputs

The session opened with the one run S75 cleared the way for: sealed w/c 0.32
with the soluble sulfates made thermodynamic, to see whether gel water is drawn
down. It did not get that far, but it stopped for a reason that redirects the
thread. What followed was a chain of small fixes the run exposed, then step 1 of
a C-S-H densification plan, which produced the evidence the rest of that plan
needs.

Commits: submodule `924de7a`, `b21ed21`; super-repo `93f67efd` (deferrals),
`a24b59fd` (pointer bump). All pushed.

## Four deferrals reviewed and committed

The MSMSE-revision entries already drafted in `docs/DEFERRED.md` were checked
against the code; every line reference held. One addition, to the micgen
`Npartc` overflow entry: the natural cap is the total voxel count, since every
particle occupies at least one voxel. Committed as `93f67efd`.

## The w/c 0.32 run

Setup: `cem151-w32-neat` (UI microstructure, verified byte-identical), sealed,
672 h target, Arcanite and Thenardite switched to Thermodynamic by removing
their `kinetic_data` blocks (that is what the UI pencil edit writes), fresh
copies of the rebuilt DCH/DBR/IPM, S75 binary. Folder
`~/tmp/thames-rh-validation/sealed-w32-thermosulf/`.

- **It passed 85 h with no timestep grind.** The S75 diagnosis (Arcanite, not
  gel water) is confirmed.
- **It stopped at 96 h, DOR 0.587**, on a space limit: CSHQ needed 2799 voxels,
  electrolyte was 0, and only 315 VOID sites passed the moisture rule.
  `Controller::doCycle` treats that shortfall as the end of the run. Internal RH
  0.902, meniscus 46 nm, 69 % of pore volume still holding water.
- **Anhydrite** hit the DC-depletion clamp 12 times at SI ~1e-5, the same class
  as S66 KL#2. Non-fatal.

So the gel-water question still cannot be asked: the lattice runs out of places
for product before gel water matters. The physical fix is C-S-H densification.

## Fixes the run exposed (submodule `924de7a`)

- **`MeniscusG0Shift(J/mol)` column in `_Humidity.csv`.** The Step 2 correction
  is confirmed live: -5.18 J/mol early, -112.4 J/mol at 96 h (RT ln 0.9557).
- **Meniscus flicker was a floating-point artifact.** `emptyPorosity` converts
  exactly the requested voxels, but the remainder came out ~1e-19 instead of 0.
  `emptySubVoxelPorosity` then subtracted it from the 1000 nm bin, where
  0.50 - (0.50 - 1e-19) is exactly 0, so the remainder never shrank and the loop
  walked down to the first bin fine enough to register it (100 nm), leaving it
  at saturation 1 - 3e-14. `getMeniscusDiameter` reported that bin, so Kelvin
  RH read 0.979 instead of 0.998 on alternate rows. Fixes: book
  `min(available, remaining)` in both sub-voxel functions; skip the sub-voxel
  step below `SUBVOXEL_REMAINDER_TOL = 1e-12` (`Lattice.h`).
- **Reported meniscus now matches the one the kinetics use.** The start-of-step
  rebuild (`KineticController::updateRelativeHumidity`) drives rates and the G0
  shift; the three writers that read the meniscus (`_SI_MeniscusCorrected`,
  `_Shrinkage`, `_Humidity`) were reading the transient state `emptyPorosity`
  leaves behind. `writeTxtOutputFiles` now rebuilds the pore-size distribution
  before them. The shift column lags KelvinRH by exactly one step, documented.
- **Provenance on the space-exhausted stop.** That path returns normally, so
  neither the exception handlers nor the fallback `finalize` ran, and
  `run_metadata.json` stayed at `in_progress`. Now it records
  `success: true`, "Simulation ended early: no room to place hydration
  products".

Verified: only the three meniscus-reading CSVs change; all others byte-identical.

## Literature (four papers, all in `~/Documents/Papers`)

Königsberger, Hellmich & Pichler, CCR 88 (2016); Muller, Scrivener, Gajewicz &
McDonald, J. Phys. Chem. C 117 (2013); Jennings, CCR 38 (2008) CM-II; Allen,
Thomas & Jennings, Nat. Mater. 6 (2007). What they settle:

- **Gel porosity is a packing property, not a Ca/Si one** (Jennings). The
  end-member `gemdcporosity` values (UI: Jennite 0.4935, Tobermorite 0.2004;
  submodule test file: the reverse) have no support either way.
- **Königsberger's master curve**: saturated gel density vs specific
  precipitation space ψ = V_w / (V_sCSH + V_w) collapses w/c 0.32-0.48 (fit to
  Muller's NMR). Regime II: ρ_B = (0.901 - 0.411ψ)·2.604 (Eq. 42). Regime III
  (no capillary space): ρ_gel = ρ_s(1 - ψ) + ψ, gel porosity = ψ, toward 0.
- **No gel-porosity floor** is stated anywhere; what stops hydration is water
  and RH.
- **Largest gel pores go first** (CM-II removes 3-12 nm pores with age; Muller
  sees gel-pore size shrink late). Inference, not a stated result.
- Muller reports no dry bulk density, so that column was dropped.

## Step 1: `_CSH.csv` gel outputs (submodule `b21ed21`)

`ChemicalSystem::getCSHGelProperties()` and `struct CSHGelProperties`. New
columns: `GelPorosity`, `SolidDensity(g/cm3)`, `SatGelDensity(g/cm3)`,
`H2O/Si`, `GelPoreSaturation`, `Psi`. ψ converts to the Allen basis (72.14
cm³/mol and 1.8 H₂O per Si) through constants local to the function; no GEMS
molar volume is read or written for it (Jeff's requirement). Cells are empty
until the CSHQ solid holds Si.

**Found along the way: `_CSH.csv` and `_CSratio_solid.csv` were frozen in
every past run.** `pGEMPhaseStoich_` was filled once at construction
(`ChemicalSystem.cc:506`) and the per-step `GEM_to_MT` fills only the
solution-phase arrays, so both files printed the CSHQ composition stored in the
input DBR (Ca/Si 1.6046) on every row. Now refreshed before writing. The real
Ca/Si in the w/c 0.32 paste runs 1.620 → 1.600; in the 11 mM Ca fixture 1.36-1.38.

Two numbers I gave earlier in the session were wrong and are corrected here:
GEMS CSHQ solid density is **2.25 g/cm³** (not 2.20, which used the frozen
columns), and THAMES C-S-H is **not uniformly 25-30 % too bulky**.

## The evidence for step 2

Sealed w/c 0.443 (`cem151-neat`, same sulfate treatment) completed 672 h, DOR
0.793, ψ = 0.506 at the end (still regime II, consistent with Königsberger's
ξ_II-III = 0.90). Figure:
`~/Research/THAMES-Tests-2026/Figures/gel_density_vs_psi.png` (script in
`Scripts/plot_gel_density_psi.py`).

- THAMES saturated gel density is **flat at ~1.715 g/cm³ for both w/c** (the
  curves coincide), because φ is composition-only and portlandite pins the
  composition.
- It **crosses Eq. 42 at ψ ≈ 0.59**: too dense early (up to ~25 % at ψ 0.94),
  too light late (~7 % at ψ 0.47).
- The first 0.3 h spike to 1.93-1.95 g/cm³ is tobermorite-rich early C-S-H with
  the lowest φ, the opposite of the measured trend.
- Matching Eq. 42 on the GEMS-solid basis would give φ ≈ 0.70 at ψ 0.9 (about
  1.9× more C-S-H voxels early) and φ ≈ 0.29 at the regime boundary (about 20 %
  fewer). Step 2 therefore changes early microstructure, setting and
  percolation substantially, not only late age.

## Open for Jeff (densification decisions)

1. Replace composition φ with φ(ψ) from Eq. 42 (changes every run)?
2. Königsberger continuous densification vs overflow-only?
3. φ floor ≈ 0 relative to the GEMS solid?
4. Remove largest gel pores first?
5. Dry bulk density — dropped (decided by omission; confirm).

Remaining steps: 2 regime II calibration; 3 regime III overflow, `wmc0_`
restamp, graceful stop; 4 pore-size distribution largest-first; 5 validation.

## Smaller items noted, not filed

- `_CSH.csv` t = 0 Ca/Si reads 1 (both moles floored at 1e-16).
- Anhydrite DC-depletion clamps in the w/c 0.32 run (KL#2 class; already on the
  audit list).
- `ChemicalSystem.cc:4453-4455` comment still says a run at 298 K writes the
  297.15 K point (S75 loose end).

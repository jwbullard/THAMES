# THAMES Project - Claude Context

## Project Overview

THAMES is a GTK-based application for advanced cement hydration simulation, using the THAMES-Hydration C++ simulator. Based on VCCTL v10.0.0; hydration engine is THAMES-Hydration (C++). Started November 2025.

## Key Differences from VCCTL

- **Hydration Simulator**: VCCTL uses disrealnew.c (C); THAMES uses THAMES-Hydration (C++)
- **Materials**: VCCTL uses per-type tables; THAMES uses a unified `material` table with tag-based classification and GEMS phase composition
- **Thermodynamics**: THAMES integrates GEMS3K (100 phases, 198 DCs, 277-353K temperature range)

## Repo layout (critical)

- `backend/thames-hydration/` is a **git submodule** (`github.com/jwbullard/THAMES-Hydration.git`). All active C++ hydration work lives here. Workflow: edit in submodule, push submodule first, then commit the pointer bump in the super-repo.
- `backend/src/` at the top level (NOT a submodule) is legacy VCCTL C — different subsystem.
- `src/app/` is the Python/GTK UI.

---

## Development History (compressed)

### Sessions 1-32 (Nov 2025 – Feb 2026): Foundation → Alpha groundwork
Repo setup + GEMS3K integration + tag-based materials architecture (S1-2). DB schema, VCCTL cement migration, PSD system, clinker fraction editor (S3-5). Phase ID mapping (0=VOID, 1=ELECTROLYTE, 2-7=Clinker, 8=AGGREGATE, 9+=Other), MicgenInputService (S6-7). Phase color service, Results Viewer (S8). Hydration Panel UI + kinetic editors (S9-10). Progress tracking, kinetic prefs, multi-select plots (S11-12). Elastic moduli UI, `bin/` standardization (S13-14). Unified voxel ordering X-fastest (S15). Multi-temperature GEMS DB 277-353K, 82 hydration products (S16). Elastic viz + 3D axes + Homebrew pinning (S17-18). Windows dev env (MSYS2 Python 3.12, PyGObject) + Unicode fixes (S19). Windows C++ build, ImageMagick→libpng, particle shapes (S20). Clang on Windows, `long int`→`long long int`, LFS (S21). W/B up to 10000 (S22). Adaptive time stepping: AdaptiveTimeController class, GEMS convergence accessors, kinetics-based initial dt, model-aware params, unified defaults (dt_initial=0.001h, dt_max=4h, growth=1.5), IC depletion recovery, exit_status.json + UI alerts (S23-30). User Manual + screenshots + config UI (S31-32).

### Sessions 33-40 (Mar-Apr 2026): Windows crash debug, feature polish
S33: micgen Windows stack overflow (stack-allocated 1.7 MB `line[]` → `static`); `-Wl,--stack,8388608`. **Windows working dir must be `C:\Users\jwbullard\Desktop\foo\THAMES`, NOT `C:\Users\jwbullard\THAMES`.** S34: suppressed_phases feature (UI unchecked → simparams.json → `addSuppressedDC` → `initDCUpperLimit` skips). S35: fixed `time_[]` overwrite with cycle times using `initialLastTime` (3 locations); macOS ad-hoc codesign in CMakeLists. S36: `time_[lastGoodI]` bounds check; kinetics floor `stepTimeTHR_=1e-5 h`; false FINAL-TIME termination requires `initialLastTime - lastGoodTime_ < 1e-6`. S37: `MAX_LATTICE_RETRIES=50`; UI polling race fix; 5 glass phases needed `(am)` suffix (C2AS, CA2S, CAS, CAS2, K6A2S). S38: **critical** — GEMS-failure recovery path bypassed kinetics timestep constraint; fix: apply `computeKineticsBasedMaxTimestep` on failure path. S39: `build-windows.sh`/`build-macos.sh`; micgen `numchunk=total/100` divide-by-zero for <100 particles; Load Operation feature. S40: 5 more VCCTL materials migrated; VCCTL removal from Materials Panel; aggregate.tar.gz (185 MB) copied; `build-macos.sh` linker race fix.

### Sessions 41-45 (Apr-May 2026): Alpha packaging + cross-platform release
S41: **Concelas** Python port (multi-scale concrete moduli from VCCTL `elastic.c:2942-3559`) → `concelas_service.py` + `concelas_runner.py`; post-completion hook after `thames -s 5`. Effective Moduli Viewer (Binder / Concrete / ITZ). Stop/cancel persistence bug fix (DB write on both paths + startup reconciliation). Help menu overhaul: `documentation_viewer.py` renders `docs/USER_MANUAL.md` to HTML via python-markdown. About dialog `&` escape. **Version `1.0.0-alpha.1`**; tag `v1.0.0-alpha.1`. `docs/ALPHA_RELEASE_PREPARATION.md` created. `docs/POST_ALPHA_TODOS.md` seeded. S42: Windows smoke test → Mix Design aggregate gating, Elastic Moduli defensive lock when no aggregate, hydration pencil-icon single-click handler, spec-file VCCTL-legacy path cleanup, Inno Setup script at `installer/thames-windows.iss`, PyInstaller GI hook needs `PATH="/c/msys64/mingw64/bin:$PATH"`, Python `zipfile` (not `tar -a -cf`), LICENSE→LICENSE.md, README rewrite. Distribution artifacts built for `v1.0.0-alpha.2`. S43: second cleanup pass — 5 partial-VCCTL cements deleted, `cement16XXX`→`clinker16XXX` rename (11 materials), SG recalc from GEMS `thames-dch.dat` (32 of 37 updated), ma157 clinker-extension backfill, `_copy_clinker_extension_data` rewritten as raw SQL, Materials Panel checkbox toggle handler + cursor preservation, per-panel info-icon anchors, `POZZOLANIC_DEFAULTS['Aggregate']` at 1e-12 mol/m²/s, app icon swap, operations wipe pre-release. S44: **Sandbox validation** found 3 crash bugs — Bug 1 empty seed DB (created `src/data/database/thames.db` 2.8 MB); Bug 2 heap corruption from BG-thread GTK calls (deleted 4 orphan statements in `_update_operation_in_database`; added `src/app/utils/thread_safety.py::assert_main_thread`); Bug 3 aggregate shape combos not refreshed post-tarball-extraction. Permanent diagnostic infra: `faulthandler` to `%LOCALAPPDATA%\THAMES\logs\thames-crash.log`, FileHandler for `thames.log`. Sandbox 3D viewer needs GPU → documented, not fixed. S45: **first public cross-platform release** — `thames-windows.spec` IS_MACOS branch fixed (VCCTL legacy executable paths → `bin/thames`, `bin/micgen`, `bin/libpng16.16.dylib`); Homebrew libpng bundling into `.app` with `install_name_tool`; **harfbuzz crisis** — replace PIL's minimal `libharfbuzz.0.dylib` with Homebrew's for CoreText support (permanent post-BUNDLE block in spec); `src/app/resources/icon.icns` created; `thames-macos.spec` deleted (canonical is `thames-windows.spec`). `dist/THAMES-1.0.0-alpha.2-macOS.zip` via `ditto -c -k --keepParent --rsrc`. Release URL: https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.2.

### Sessions 46-49 (May-Jun 2026): Diagnostics, bug hunt, brainstorms
S46 (May 11-12): 3D viewer color-button silent crash (dev mode only) — GLib abort from missing `org.gtk.Settings.ColorChooser` schema in Ghostty's XDG_DATA_DIRS; fixed in `src/main.py` (dev mode + macOS → set `GSETTINGS_SCHEMA_DIR`). Bundled `.app` unaffected. Kinetic-editor save bug: Hydration panel's kinetic dialog never persisted to `kinetic_defaults.json` (Preferences did); fix in `thames_hydration_panel.py::_on_configure_kinetics` calls `set_user_default` in both OK branches. **Cement+silica-fume cycle-11 stall** diagnosed as GEMS-degenerate landscape oscillation; workaround `Portlandite→Thermodynamic` cleared it. See `docs/session46_summary.md`. S47 (Jun 4): Mix Design 32³ silent-failure — stale legacy `system_size: int = Field(ge=50, le=500)` in `src/app/models/mix_design.py` while per-axis fields allow `ge=25`; fixed to `ge=25, le=400`. Silent-failure UX added to POST_ALPHA_TODOS. `release-notes-alpha-3.md` workflow started; amended published alpha-2 release notes via `gh release edit`. ThamesRender scoped as separate project at `~/Code/ThamesRender/`. S48 (Jun 7): THAMES architecture triangle SVG (dark + light) for slides — `docs/scripts/build_triangle_svgs.py`. Affinity Designer quirks baked into builder: tspan superscripts broken → use matplotlib PNG; CSS `font-family` ignored → inline attribute per `<text>`; CSS `fill` unreliable → inline `fill=`. S49 (Jun 12): Transport-controlled kinetics brainstorm — the well-mixed-electrolyte compromise. Full verbatim conversation `docs/transport_kinetics_brainstorm.md`. Recommended sequence (endorsed): trap detector (later abandoned — wmc mechanism already handles it), per-phase shell δ + series resistance, effective-area sanity check, HydratiCA as validation oracle.

### Session 50 (Jul 20): Classical Nucleation Theory design + Python prototype
New multi-session thread targeting `StandardKineticModel` and `PozzolanicModel` (PK excluded — Avrami-Cottrell absorbs nucleation). Committed 8-step plan and calibrated portlandite defaults (γ=0.044 J/m², A₀=1e30 /(m³·s), θ=180° homogeneous, V_m=33.08 cm³/mol from CemData18). Prototype at `~/Research/THAMES-Tests-2026/Scripts/NucleationCNT-Prototype.ipynb`. Design decisions: anonymous scalar accumulator per phase + batched simultaneous placement; NOT per-voxel fractional occupancy; uniform-random placement over electrolyte for portlandite; **CNT drives adaptive dt (Option C, shrink-and-retry, NOT silent cap)**; every parameter as `{value, range, provenance}` JSON. Full narrative: `docs/session50_summary.md`.

### Sessions 51-54 (Jul 23-28): CNT integration → SaturatingRateModel → JMAK
**S51** (submodule `53e0ee2`): CNT rate calc + placement + adaptive-dt cap in Standard + Pozzolanic; four virtuals `computeNucleationVoxels/hasNucleation/accumulateNucleation/drainNucleationInteger`. CNT-off byte-parity preserved. **S52** (submodule `0754968`): `SaturatingRateModel` — Bullard 2015 CCR Eq. 2 / Han 2025 CEJ Eq. 7. `r = k(1 − exp[−(−B ln Ω)^n])` saturates at k. Asymmetric dissolution/precipitation blocks. Portlandite calibration k=4.05e-4, B=0.74, n=1.9. `docs/SATURATING_RATE.md`. **S53** (submodule `7f7c6d8`): CNT scaling fix — two independent bugs. (A) CNT placement used physical `vVoxel/vMolar` for moles but THAMES stores DCMoles/microPhaseMass/scaledMass in a **per-100-g-solid normalized frame** (`Lattice::normalizePhaseMasses`) — off by ~10⁷×. (B) `ChemicalSystem::calculateState` skips `GEMPhaseVolume→microPhaseVolume` fill for kinetic phases; CNT-only zero-mass phases had stale `microPhaseVolume_=0`, causing all placed voxels to dissolve same cycle. Plus PozzolanicModel throw-to-DOR-zero guard for `initScaledMass_=0`. **S54** (submodules `22c65a7`, `9a2d2a9`, `d743756`, `9c3cc3c`): pivot to **JMAK-per-voxel** as the correct sub-voxel model. Pure-math free functions in `namespace jmak` (`src/thameslib/JMAKGrowth.{h,cc}`); Cohort→Generation rename; `getNucleationRate(S)` + `getGrowthVelocity(S)` virtuals added to `KineticModel` with defaults 0; overrides in Standard/Pozzolanic/SaturatingRate. `JMAKParameters` optional in `KineticData` (n ∈ [2.5, 4], α default 4π/3). Per-phase JMAK state in `KineticController`. Dispatched from CNT block: `if (jmakEnabled_) updateJMAKPhase() else classical`. Backward compatible. `docs/jmak_moment_decomposition.tex` derives moment identity for time-varying J and G. All gates pass. **Not yet turned on for any production phase.**

### Session 55 (Jul 29-30): Mass-balance fix, transport-kinetics 3-phase plan, pure-alite validation
Three-headed session. Full narrative: `docs/session55_summary.md`.

- **Mass-balance fix** (submodule `94bd4b0`, super-repo `f1d2609b`). Symptom: HEN carbonation produced 995,932 voxels of Calcite from 374 voxels of Portlandite (200× stoichiometric excess). Root cause: JMAK/CNT precipitation and Standard/SR dissolve+precipitate paths wrote only to `DCMoles_[solid]` and locked GEMS via `setDCLowerLimit/setDCUpperLimit`; the aqueous IC counterpart was never adjusted, so GEMS "reconciled" by inflating bulk composition ("phantom Ca"). Fix in `KineticController`: (1) `solidICAvailabilityScale(DCId, moles_wanted)` dry-cap in [0,1]; (2) `commitSolidICTransfer(DCId, delta)` atomic aqueous↔solid transfer with H⁺/OH⁻ charge compensation; (3) every kinetic path routed through it with fail-loud overdraft. **Session-46 silica-fume cycle-11 oscillation is fully resolved by mass balance alone** — SI(Portlandite) bounded ~1% around 1.0. Session-47 encapsulated-remnant NOT resolved (it's a shell-diffusion problem — trapped ettringite has `wmc_ > 0` because surrounding C4AsH14 is porous, so it IS in `dissolutionSites_`).

- **Transport-kinetics 3-phase plan implemented end-to-end** (plan `~/.claude/plans/effervescent-forging-diffie.md`, submodule commits `43dd74c`/`5fbb4b6`/`0185cf8`/`1bdf5d5`, super-repo pointer bumps `37142c57`/`2e4cdc20`/(none)/`863a579d`).
  - **Phase 1** (`43dd74c`): per-site shell thickness δ from lattice topology using **ball-centroid outward-normal method** (Bullard's suggestion, tunable `r` default 2.5 voxels). New `TransportStats.h/.cc` POD types + `aggregateShellDistribution` (equal-frequency K-bin histogram, default K=5) + `Lattice::estimateOutwardNormal`, `walkToElectrolyte`, `computeShellStats`. Unit tests `test_transport_stats` (6 groups).
  - **Phase 2** (`5fbb4b6`): optional `transport` sub-block in `kinetic_data` JSON with `{value, range, provenance}` pattern (matches nucleation). `TransportParameters.h`, `TransportCorrection.h/.cc` skeleton, `KineticController::parseTransportBlock`, `KineticData.h` optional, `ChemicalSystem::getDCIdOrMinusOne` for graceful DC lookup.
  - **Phase 3a** (`0185cf8`): `TransportCorrection.cc` fleshed out — `solveSurfaceConcentrationLinear` (closed form), `solveSurfaceConcentration` (Brent 60-iter, 1e-8 rel tol), `shellCorrectionFactor` (per-bin `Da = k·δ/(D_eff·C_eq)`, factor = `Σ siteFraction/(1+Da)` normalized; **zero-δ bins contribute 1.0** — no diffusion resistance when a site touches electrolyte directly). Unit tests `test_transport_correction` (8 groups).
  - **Phase 3b** (`1bdf5d5`): shell correction wired into `StandardKineticModel::calculateKineticStep` (line 214), `SaturatingRateModel::calculateKineticStep` (line 128), `PozzolanicModel::calculateKineticStep` (line 307) as `area *= shellCorr` gated on `transport_.has_value() && limitingDCId_ >= 0`.
  - Byte-parity preserved on CNT-off `HY-ccr152-ws45` 17/17 CSVs first 11 cycles when `transport` block absent.

- **Pure-alite paste test system** (Jeff built two 100³ microstructures: `AlitePaste-w45` w/c=0.45, `AliteSphere` single 50-voxel-Ø sphere). Alite as SaturatingRate with Han-2025 params (k=1.253e-4, B=0.0475, n=3.73, Ea=41570 J/mol, dissolvedUnits=4); CSHQ + Portlandite Thermodynamic. Shell variant adds transport block `D_eff=1e-13 m²/s` (Jeff-confirmed Ca²⁺ through mature C-S-H), `limitingDC="Ca+2"`. **First-launch bug**: **phase IDs must be contiguous 0..N-1**; I gave CSHQ id=9 and Portlandite id=10 → array-index crash. Renumbered 3 and 4.
  - **1-day results**: Alite DOR 23.46% (baseline) vs 23.50% (shell) — 139 voxels of 415,957 = 0.04 pp delta. Effectively no throttle. Two root causes: (1) **Geometric** — mean CSHQ shell thickness at 24 h ≈ 0.82 voxels; distribution dominated by δ=0 bins. Jeff's insight: "If the mean shell thickness is less than 1 voxel... there is basically no shell." (2) **Mathematical** — `C_eq = C_bulk / S^(1/stoich)` collapses for far-from-equilibrium phases (Alite S≈1e-14 → derived C_eq ≈ C_bulk × 1e14 → Da ≈ 1e-9 → factor ≈ 1). The physically-correct C_eq for the transport half-cell should come from a **reference sink phase** (Portlandite for Ca²⁺; ettringite/AFm for SO₄²⁻; calcite for CO₃²⁻), not from the reactant phase's own SI.
  - **28-day shell run** terminated at t=148 h (6.17 d) — all Electrolyte voxels consumed by product growth. Final Alite DOR 78.7%, CSHQ 70.9% vol frac, Portlandite 20.3% vol frac. Baseline-28d comparison: shell delta at 6.17 d = +281 Alite / −0.07 pp DOR — direction correct, magnitude still tiny (0.07% relative).

- **C3S ln K inconsistency between GEMS and SR calibration** (BLOCKER for further shell work). GEMS CemData18 gives **ln K = −24.4** for `C3S + 5 H₂O → 3 Ca²⁺ + H₄SiO₄ + 6 OH⁻`; Perry/Nicoleau/Nonat calibration gives **ln K = −50.7**. Δ = 26.3 (~11 orders of magnitude in K). PK masked this because it doesn't use SI; Standard/SR now expose it. Two fix paths: (1) rescale SR params to match GEMS's ln K, or (2) override G°(C3S) in DCH file (+65.2 kJ/mol) so ln K = −50.7. **Must resolve before pushing on C_eq design question.** Same audit needed on every other Standard/SR phase (Portlandite, ettringite, CSHQ products, gypsum, ...).

- **Priority-2 mass-balance rerun** (silica-fume Portland 200³ 28-d, `~/tmp/thames-mb-portland-sf15`) completed successfully — 25,030 cycles, dt_final=4.0h, only 4 IC depletion events (vs 20+ in first 4 min of Session-46's failing run). CSHQ 66.4% vol, Portlandite 5.2%, Sfume unreacted 5.1%. Confirms mass-balance fix works end-to-end.

### Session 56 (Jul 31, 2026): C3S ln K correction in DCH, calorimetry preserved
Single-focus session resolving S55's BLOCKER on C3S ln K. Also compressed CLAUDE.md at session start (89k → 22k chars). Full narrative: `docs/session56_summary.md`.

- **Analytical framing**: pure B/n rescaling of SR params (Jeff's initial preference — keep k as infinite-dilution measured) is mathematically incompatible with matching Bullard 2015 Figure 1 when ln K shifts by Δ ≠ 0. The SR law's `r = 0 at Ω = 1` anchors the zero-rate crossing at whatever K the database provides — no (B, n) choice can shift it. Approximate fit possible with n ≈ 9.8 (vs paper's 3.73), but the shape change is a numerical artifact with no physical interpretation.
- **DCH edit** (`src/data/gems/thames-dch.dat`, DC index 118, file line 682): uniform **−65,211.81 J/mol** offset applied to G°(C3S) at all 39 T grid points. ln K at 298.15 K now **−50.70** exactly (was −24.39). SI(C3S) throughout THAMES shifts by factor exp(26.3) ≈ 2.65e11. Only line 682 differs vs backup; CRLF line endings preserved; backup at `src/data/gems/thames-dch.dat.pre-c3s-lnK-fix-20260731` (gitignored). **Sign to remember**: G° decreases (mineral more stable) to make ln K more negative — got this wrong once in an explanatory paragraph; verified via direct computation.
- **Calorimetry preserved (unexpected)**: Jeff flagged that microcalorimetry validation needs accurate ΔH°_rxn. Direct check: paper ΔH°_rxn(H3SiO4⁻ form) = −137 kJ/mol vs GEMS translated (HSiO3⁻ form) = **−135.8 kJ/mol**. 1.2 kJ/mol discrepancy = within paper precision. Babushkin's H°(C3S) was already correct. The ln K discrepancy is a **reference-state offset in CemData18's G0/H0/S0 storage** (G0 and H0−T·S0 differ by +131 kJ/mol constant across species — a GEMS convention, not physical error). No H0 correction needed; calorimetric prediction dq/dt = ΔH°_rxn · dξ/dt now correct (uses G0 → SI → rate = corrected; uses H0 = Babushkin ≈ correct).
- **Portlandite K spot-check**: log Ksp = −5.2004 (GEMS) vs CemData18 target −5.20 (exact), Sipos 2006 −5.19, Duchesne & Reardon 1995 −5.29. ΔH°_rxn = −18.4 kJ/mol matches Sipos calorimetric ~-18. **No correction needed.** Hypothesis: Babushkin heritage issue is specific to anhydrous clinker phases (C3S, C2S, C3A, C4AF); aqueous-in-equilibrium phases (Portlandite, gypsum, ettringite) measured near ambient are fine.
- **JMAK-Portlandite sanity (running at session end)** at `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/sanity-3h/`, finaltime = 3 d. At t=3.07 h, SI_Portlandite = 13.3 and **declining** (was 13.6 at 2.81 h). Prior 4b run (Jul 28) hit 1632 and climbing at same t. **Session-55 mass-balance fix has cured the SI runaway.** Will finish overnight; compare vs Session-46 ~14% Portlandite target at 24 h in Session 57.
- **Pure-C3S sanity v2** at `~/tmp/thames-pureC3S-sanity-v2/`: all product phases suppressed → Alite dissolves via SR into pool that accumulates ions. SI trajectory grew smoothly 3.6e-13 → 0.078 over 12 h, no overshoot, rate slowing asymptotically as Ω→1. Confirms corrected K produces physically sensible driving forces. First attempt (v1) blew up to Ω=505 in a single step because `dt_initial=0.0001 h` was silently ignored — v2 workaround: outtimes[0] = 1e-7 days forces tiny first cycle.
- **POST_ALPHA_TODOS additions (3)**: (1) audit remaining Standard/SR phases (C2S, C3A, C4AF, ettringite, gypsum, CSHQ end-members) for ln K discrepancies using the C3S procedure; (2) audit H0 for calorimetric ΔH°_rxn targets across same phase list; (3) `dt_initial` parameter is silently ignored by AdaptiveTimeController — first cycle sized by first outtime — workaround with tiny outtimes[0].
- **Discovery worth remembering**: at high Ca+Si concentrations most Si goes into the CaSiO3@ ion-pair complex, not free SiO2@ or HSiO3⁻. GEMS accounts for this properly. But "free silica" concentrations in Solution.csv can be misleading — sum all Si-bearing DCs (AlHSiO3+2, AlSiO5-3, CaSiO3@, MgSiO3@, HSiO3−, SiO2@, SiO3²⁻) for total aqueous Si.

### Session 57 (Aug 6, 2026): C3A ln K correction (Ye 2022), pure-alite rerun, Garrault validation
Continuation of ln K audit thread + deep validation work establishing pure-C3S semi-quantitative credibility. Full narrative: `docs/session57_summary.md`. Commit `e1128b48`.

- **JMAK-Portlandite sanity from S56 completed cleanly overnight**: 72 h in 6227 cycles, SI(Port) peaked at 11 and decayed to 1.2 (vs pre-mass-balance-fix 1632 climbing). Portlandite 5.05% total vol at 24 h vs S46 target ~14% (under-hit but no runaway). **Mass-balance fix from S55 fully cured the SI runaway.**
- **K audit of remaining Standard/SR phases.** Anhydrite, Gypsum, Portlandite, Ettringite, Calcite all match published Ksp within 0.005 log units — **no corrections needed.** Pattern confirmed: Babushkin heritage discrepancy is systematic only to anhydrous clinker phases (C3S, C2S, C3A, C4AF). C2S and C4AF audits inconclusive — need calibration papers not yet available.
- **C3A ln K correction** using Ye et al. 2022 CCR (Jeff coauthor) as calibration source. Reaction `C3A + 2H2O → 3Ca²⁺ + 2AlO2⁻ + 4OH⁻`; Ye reports experimental ln K at 4 temperatures (283-313 K). GEMS gave +34.57 (unphysical — would need 45 M Ca²⁺ at equilibrium); Ye's ln K at 298 K = −48.75. Discrepancy 83 ln units (36 orders of magnitude in K). Applied constant offset **−206,549.59 J/mol** to G°(C3A), DC[117]/line 681. Backup at `src/data/gems/thames-dch.dat.pre-c3a-lnK-fix-20260806`. Option A (constant shift) chosen over T-varying because Ye's three candidate T-dependence models diverge by 22 ln units above 40 °C and one has hard domain error below 281 K. Practical impact today: none (C3A uses PK in production; correction is prerequisite for future SR migration).
- **Sign verification.** Explicitly re-derived Portlandite log K = −5.2004 from same formula/sign convention → matches CemData18 exactly. Confirms C3A +34.57 is genuinely what CemData18 gives (not a sign flip Jeff worried about).
- **Pure-alite paste rerun** at `~/tmp/thames-alite-baseline` and `~/tmp/thames-alite-shell` with corrected DCH. **SI(Alite) shifted exactly by exp(26.3)** (2.669e11 measured vs 2.652e11 theoretical, 0.6% error). But: Alite DOR at 24 h dropped from 23.23% (pre-fix) to 0.197% (post-fix) — **118× slower**. Shell throttle now shows 40% relative reduction (vs pre-fix's noise-level 0.13%). Pre-fix rate happened to match experiment BY ACCIDENT (unphysical SI=1e-14 → SR at 99% of k always). Post-fix rate is physically correct SR response for a paste held at CH+CSHQ saturation.
- **JMAK-CH pure-alite test — worse, exposed bootstrap deadlock.** Turned Portlandite on with JMAK+CNT (same params validated in S56 sanity). Portlandite NEVER nucleated; SI(Port) plateaued at 4.12 (below CNT threshold ~10). Without CH buffer, [Ca] climbed 16 → 27 mM → SI(Alite) rose → dissolution slowed further. **Pure-alite is structurally hard for THAMES:** single Ca source can't drive SI(Port) high enough to trigger CNT nucleation, but the Ca supply from Alite dissolution itself is throttled by SI(Alite). Chicken-and-egg deadlock.
- **Garrault-Nonat 2001 validation** (Jeff's proposal to sidestep the deadlock). Paper `~/Documents/Papers/Garrault/Garrault_2001_Hydrated_layer.pdf` reports controlled-[Ca] pure-C3S dissolution: peak [Si] = 85 μM at 11 mM Ca(OH)2, 35 μM at 22 mM. Set up `~/tmp/thames-alite-Ca22mM` and `~/tmp/thames-alite-Ca11mM` using `electrolyte_conditions` with `"condition": "fixed"` for Ca²⁺, CaOH⁺, OH⁻ (Jeff's split 17/5 for 22 mM; proportional 8.5/2.5 for 11 mM; charge balanced). **Peak [Si] MATCHES: 85.5 vs 85 μM at 11 mM (1% agreement), 31.9 vs 35 μM at 22 mM (10% agreement).** Direct fingerprint of the SR + corrected-K dissolution rate. **THAMES's pure-C3S credibility is now established.**
- **CSHQ [Si] decay NOT captured.** Garrault shows [Si] drops from peak to plateau (85 → 45 at 11 mM, 35 → 20 at 22 mM) over 5-30 min. THAMES stays flat at peak. CSHQ was Thermodynamic — GEMS's CSHQ K at imposed [Ca] gives equilibrium [Si] near maximum-supersaturation curve, not solubility curve. **This is exactly what a JMAK-CSHQ implementation would fix** (analogous to JMAK-Portlandite from S54).
- **`electrolyte_conditions` "fixed" mechanism has a bias bug (POST_ALPHA_TODOS entry added).** In `ChemicalSystem::setElectrolyteComposition` (line 4415-4448), the code sets `DCMoles_[fixedDCId] = target` but only tops up `ICMoles_` when target > current — never reduces when target < current. Result: when a reactant dissolves and pushes concentration above target, GEMS is free to redistribute the un-removed IC pool back into aqueous phase. Observed ~10% bias (Ca22mM held at 23.55 instead of 22; Ca11mM at 12.05 instead of 11). Never exposed before because no test config uses `"condition": "fixed"`. Fix: add symmetric IC-reduction branch, optionally also constrain DCUpperLimit_.

### Session 58 (Aug 21, 2026): NIST-user diagnostic → provenance infrastructure + F1/F2 fixes
Full narrative: `docs/session58_summary.md`. Commits: submodule `0d2013b` + `2da613a`, super-repo `868e9cba` + `ab706fad`. Nothing pushed.

- **NIST diagnostic thread** opened after Jeff received a NIST user's operations folder (`~/tmp/NIST-thames-operations/operations/`). Set up `docs/NIST-diagnostic.md`. Four bugs identified from log-only inspection: **A** parseMicroPhases fatal on `C2AS(am)` glass-phase configs (Hydration-sphere and -test-2 fail, PLC-based -test-1 succeeds); **B** `cp`/`mv`/`mkdir -p` shell-outs in `backend/thames-hydration/src/thames.cc` (9 sites) unrecognized on Windows cmd.exe; **C** no `exit_status.json` in any Result folder; **D** duplicate `Hydrotalc-pyr` + `hydrotalcite` in configs.
- **Bug B drafted (NOT applied).** `scratchpad/thames-cc-portability.patch` — replaces shell-outs with `std::filesystem` (C++17 already enabled). Three helpers (`copyFileInto`, `moveFileInto`, `ensureDir`) preserve `FileException` error path. Also flags an ifstream-close-before-rename sequencing fix needed on Windows. Awaits Jeff's one-more-look.
- **Provenance-sidecar infrastructure landed end-to-end** — the big scope of the session. Motivation: Bug C plus the direct NIST-diagnostic pain of "did you build these with the same THAMES?" Eight design decisions made with Jeff (revised item 6 from coexist to replace on merits). New backend files: `RunMetadata.h`/`.cc` (~280 lines), vendored `picosha2.h` (MIT SHA-256), `version.h.in` (CMake-generated identity). Modified: `CMakeLists.txt` (git rev-parse + build date via `configure_file`), `thames.h`/`.cc` (init + finalize hooks on hydration and elastic paths), `Controller.{h,cc}` (removed `writeExitStatus`; 15 CSV writers get `runmeta::csvCommentLine()`). Result: `Result/run_metadata.json` sidecar per operation + one-line `#`-comment header on every CSV. `exit_status.json` fully replaced (per decision 6b).
- **UI plumbing:** `hydration_input_service.py` injects `ui_context` block into `simparams.json` at operation launch (UI version, python version, platform.system/release/machine, hostname, operation_name). `user_config.py` gains `include_hostname_in_metadata` (default True). Preferences dialog gains hostname toggle in General tab. `operations_monitoring_panel.py` reads `run_metadata.json` instead of `exit_status.json`. 17 CSV consumers (12 files) hardened: 3 pandas gain `comment='#'`, 14 `csv.reader`/`DictReader` gain a skip-`#` generator idiom.
- **Regression proof (Phase 3).** Ca11mM smoke fixture, 27 s wall. **29/29 CSVs byte-identical to Session 57 baseline** after accounting for the new `#` header. DCH sha256 (`553987f3…`) exactly matched `shasum -a 256`. Zero simulation-output regressions.
- **Compiler/flags identity added (schema_version 1 → 2, second commit).** New `"build"` block records `compiler_id`, `compiler_version`, `cxx_flags` (verbatim `CMAKE_CXX_FLAGS`), `cmake_version`, `build_type`. Required moving `configure_file` in CMakeLists to run AFTER compiler branches, and mirroring `add_compile_options` into `CMAKE_CXX_FLAGS` on Clang so the flag string is captured (Clang branch previously left it empty).
- **F1 — early-crash provenance (SHIP-BLOCKER for NIST diagnostic value).** `runmeta::initialize` was called AFTER `prepOutputFolder`, but `ChemicalSystem` construction (where Bug A throws) happens much earlier. Bug-A-class crashes left zero provenance. Fix: moved initialize to fire right after `simParamName` capture, BEFORE `ChemicalSystem`. Added specific `runmeta::finalize` calls in each ChemicalSystem catch block with reasons like `"ChemicalSystem constructor: DataException"`. Made finalize idempotent (first-call-wins). Added generic fallback finalize at top of `deleteDynAllocMem`. **CRLF fix:** `extractDchName` now `rstrip`s trailing whitespace on all path arguments — `getline(cin, ...)` on POSIX keeps `\r` from Windows-authored `input.in` files, so paths like `"thames-dat.lst\r"` don't exist. Verified with Bug-A trigger (UI-selected glass phase): sidecar correctly populated with specific reason, DCH sha256, build identity.
- **F2 — Running → Pending on backend crash (SHIP-BLOCKER, fixed).** Root cause: two `status_mapping` dicts in `operations_monitoring_panel.py` (lines 5623 and 5853) were missing `'ERROR'`. `hydration_executor_service` writes DB status `"ERROR"` on crash (per `models/operation.py:25` documented alias for FAILED); reader's mapping fell through to `PENDING` default; polling loop overwrote in-memory RUNNING with PENDING; `_validate_operations_data` zeroed the progress. Result was "Pending 0%" indefinitely on any real crash. Fix: added `'ERROR': OperationStatus.FAILED` to both dicts, swapped silent fallback for logged warning.
- **Microstructure-restoration ship-blocker (elevated + fixed same session).** Load Operation populated all sim settings but silently kept whatever microstructure was in the (now-disabled) picker — scientific-reproducibility footgun. Fix: `HydrationInputConfig.microstructure_file` field added; new `_restore_microstructure_for_loaded_op` helper reads the field first, falls back to parsing line 4 of `input.in` for legacy configs, looks up basename in library combo then in operation folder itself, programmatically fires `changed` signal so downstream state updates. Strong warning on failure, confirmation on success. Jeff-verified.
- **Late-session Bug A root-cause candidate.** Jeff's Zoom with NIST user surfaced that **Windows UI auto-includes glass phases (CAS2 and others) as hydration products even when not in the initial microstructure**; macOS UI does not. Almost certainly Bug A itself: Session 37 added `(am)` suffix to five glass phases; if Windows UI injects without the suffix or without checking the microstructure, backend receives an unmatchable name → `parseMicroPhases` throws exactly the observed error. Logged in NIST-diagnostic.md and POST_ALPHA_TODOS with concrete investigation plan.
- **Phase 4 UI integration tests:** Test 1 (happy path) PASS, Test 2 (failure banner) PASS after F1+F2, Test 3 (hostname toggle) PASS after fixing my `get_config_manager` bug (I called a nonexistent function; correct is `get_service_container().config_manager`), Test 4 (legacy op) READ-VERIFIED (surfaced the no-import-workflow gap), Test 5 (CSV consumers) PASS (surfaced pH/DOR-not-plottable gap).
- **POST_ALPHA_TODOS additions (5):** Windows glass-phase auto-inject (Bug A candidate); Preferences Apply/OK/Cancel UX (Jeff OK'd as-is); no "Import operation from folder" workflow; pH/DOR not plottable; microstructure ship-blocker (LANDED same session).
- **Ship-blockers still open before NIST alpha-3 distribution:** (1) Bug B application, (2) Windows glass-phase auto-inject investigation. Both fixable in a single follow-on session.
- **venv rot side quest:** `thames-env` mixed 3.11/3.14 with 3.11 site-packages only — nuked and rebuilt against Python 3.14. Added missing `psutil` to `requirements.txt` (was only in `thames-windows.spec:93` hidden imports).

### Session 59 (Aug 22, 2026): NIST alpha-3 ship-blockers closed (Bug A + Bug B + electrolyte-fixed)

Three fixes landed for the NIST alpha-3 push. Full narrative: `docs/session59_summary.md`. Nothing yet committed at time of wrap-up doc.

- **Bug B application (LANDED).** S58 draft patch from `scratchpad/thames-cc-portability.patch` applied to `backend/thames-hydration/src/thames.{cc,h}`. Replaced 9 shell-out sites (`mv -f` ×2, `cp -f` ×6, `mkdir -p` ×1) with `std::filesystem` helpers `moveFileInto` / `copyFileInto` / `ensureDir`. `<filesystem>` added to `thames.h`. C++17 already enabled → no linker flag needed on macOS/Linux/Windows-MSVC/MinGW. Preserves the existing `FileException` error path. Also deleted dead `string buff = ""` / `int resCallSystem` locals in `deleteDynAllocMem` that fell out of use after the shell-outs. Verified on macOS via the Ca11mM smoke fixture (27 s, exit 0, all copies + move landed correctly). Windows validation deferred to Jeff's next Windows session.

- **Bug A (parseMicroPhases glass-phase crash) LANDED via DCH-rename path.** Diagnosed as UI–DCH naming mismatch: S37 added `(am)` suffix to the 5 glass phases in the UI dicts but never propagated to the DCH's PHNL/DCNL or the DB's `material_phase` rows. `build_gemphase_data("C2AS(am)") → get_phase("C2AS(am)")` returned None because DCH held bare `"C2AS"` → simparams.json entry lacked `gemphase_data` → backend `parseMicroPhases` threw. Not Windows-specific — the crash fires on any platform with any config putting `(am)`-suffixed glass phases into `hydration_products`. Windows-only was just the trigger (UI auto-inject Jeff observed on his Zoom call). Full analysis in `docs/NIST-diagnostic.md`. **Fix direction chosen: edit the DCH, not the UI.** Jeff clarified he already maintains a private fork of CemData18 (added several glass phases himself originally), so the "don't fork CemData18" concern was moot. Aligning DCH with the UI's convention keeps a single naming convention flowing unmodified end-to-end — no `.replace("(am)", "")` kludges. Rename scope: DCH PHNL+DCNL (20 subs), DBR (10 subs), DB `material_phase` for ClassF-FlyAsh (2 rows), `simparams_service.py::_get_thamesname` (deleted 5 mappings), `ChemicalSystem.cc::colorN_["..."]` hardcoded initializers (18 live + 15 commented-out subs). Backups saved as `*.pre-glass-am-rename-20260822` and gitignored. **Two local user microstructures** (`OPC-FA-30`, `HY-OPC-FA-30`) had bare glass names in `_phase_mapping.json` — moved to scratchpad; will need regeneration on demand. **Byte-parity verified:** 26/29 CSVs identical to pre-rename baseline; 3 that differ do so ONLY in glass-phase column-header names. Zero simulation-data regression. **POST_ALPHA filed:** "Eliminate hardcoded phase-name strings in ChemicalSystem.cc" — the `colorN_` / `elasticModuli_` initializer blocks are the deeper class of fragility that made this fix necessary.

- **Windows glass-phase auto-inject: downgraded, not gone.** Bug A crash closed by the rename. But the underlying Windows-only bug (UI auto-adds glass phases the user didn't select) is now a cross-platform reproducibility bug: Windows simparams.json ≠ macOS simparams.json for identical UI inputs; different phase-ID assignments; different `suppressed_phases` lists. SI(glass) in Portland pore solution is very low so user-visible physics divergence is unlikely but not proven zero. Still needs fixing before beta or any cross-platform validation study. Investigation deferred to next Windows-access session.

- **Fix C (electrolyte-fixed bias) LANDED.** S57-diagnosed asymmetric IC-transfer in `ChemicalSystem::setElectrolyteComposition`. Removed the `if (deltaDCMoles > 0)` gate at ChemicalSystem.cc:4431 — both directions of transfer now work. Ca11mM bias 12.05 → 11.58 mM (10% high → 5% high), Ca22mM bias 23.55 → 23.22 mM (7% high → 5.5% high). Peak total_Si preserved (Ca22mM 32.20 vs S57 31.9 μM; Ca11mM 104.6 vs S57 85.5 μM — the Ca11mM increase is physically consistent with Ca being closer to target 11 mM shifting CSHQ-eq [Si] up). **DC-bounds pinning attempted at ±1e-15, ±1%, ±5% and REVERTED.** Tight bounds cause GEMS convergence failure (three interdependent pinned Ca species over-constrain the K equilibrium); loose bounds (±5%) let GEMS solve but Alite dissolution collapsed to ~0% DOR because pinning aqueous Ca+2 blocks kinetic dissolution products from leaving the aqueous phase. The correct semantics for `condition: "fixed"` is "external reservoir absorbs/supplies", which the symmetric IC-transfer alone models correctly.

- **Personal-lesson diversion: phantom peak-Si "regression".** Spent ~30 min bisecting a nonexistent regression. Reported Ca11mM peak = 4.9 μM after Fix C vs S57's 85.5 μM. Bisected submodule all the way back to S57's own `1bdf5d5` — same 4.9 μM. Then realized I was summing only free-Si species (`SiO2@ + HSiO3-`). Adding `CaSiO3@` (72 μM at high [Ca]) + `MgSiO3@` (7.8 μM) — which S56 CLAUDE.md warned about explicitly — recovered peak = 85.48 μM matching S57. Zero physics regression ever existed. **POST_ALPHA filed:** add derived per-element total columns (`total_Si`, `total_Ca`, etc.) to `Solution.csv` computed as `Σ DCMoles × getDCStoich(dcId, icId)`. Also written up as `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/reference_total_si_accounting.md`.

- **Ship-blocker status for NIST alpha-3:** Bug A CLOSED, Bug B CLOSED, Fix C LANDED. Nothing else blocks the alpha-3 push from a code standpoint. **Residual verifications:** Windows validation of Bug B + Bug A fixes; Windows glass-phase auto-inject investigation.

### Sessions 60-62 (Aug 23-25, 2026): Windows-hotfix cycle for NIST tester

Three sessions across Mac and Windows. Full narrative lives in the memories `project_nist_patch_state.md`, `project_alpha2_macos_followup.md`, and the commit range `53abf4dc..238389b5`.

- **S60 (Aug 23, mac).** Two docs authored: `docs/CNT_DIAGNOSTIC_PLAN.md` (portlandite zero-placement investigation, deferred until Windows work clears) and `docs/session61_windows_prep.md` (OS-switch friction reducer). Two mac reference `simparams.json` files committed under `docs/reference_data/` for the glass-phase auto-inject diff (`mac_reference_today.json` primary, `mac_simparams_reference.json` secondary pre-S59 corroboration). New scope-discipline memory `feedback_thames_scope_discipline.md` capturing THAMES's four-way moat, three go-to problem sets, HydratiCA correction, and mission-creep guardrails.

- **S61 (Aug 24, Windows).** Three ship-blockers landed for the NIST alpha-3 push. (i) Submodule `fbf392b`: `-lws2_32` link for MinGW's `gethostname` — without it, the entire Windows C++ backend fails to link. (ii) Superproject `60f8de26`: micgen.c triple-fix (double-free-of-globals NULLs, particle pointer-array bounds using actual Npart not NPARTC, fclose-before-freemicgen write ordering) + `build-windows.sh` bundling of the full MSYS2 runtime DLL closure (libwinpthread, libgcc_s_seh, libstdc++, zlib1). All three micgen bugs are cross-platform latent — masked on macOS by the more permissive allocator/stdio. (iii) Superproject `7a9ba095`: migration `20260824_01_glass_phase_am_rename` for `material_phase.gem_phase_name` — S59's phase rename in DCH/DBR/seed-DB/C++ never wrote a migration for existing users' local DBs, so any material composition with bare glass names produced empty `gemphasename` → S59 Bug A resurfacing. **The migration was written into `MigrationManager.upgrade_database()` but not verified to actually be called at startup — that gap surfaced in S63 (see below).** Three POST_ALPHA entries added: phase-rename checklist, ferrite/small-phase abort (superseded by S62), run_metadata.json not finalized on kinetics abort path (superseded by S62).

- **S62 (Aug 25, Windows).** Three more fixes + hotfix ship. (i) Submodule `6f40f4a`: `KineticController::calculateKineticStep` DC-depletion clamp — was `exit(0)` when `keepNumDCMoles < 0`; now clamps `numDCMolesDissolved` to `DCMoles_[DCId]` and continues with a WARNING. `commitSolidICTransfer` reordered to run AFTER the clamp so aqueous side receives clamped transfer. Second exit path (`scaledMass < 0`, kept as genuine failure signal) now calls `runmeta::finalize(1, "...", diag)` before `exit(1)` — matching the S58 ChemicalSystem-catch pattern. (ii) Superproject `f21c773d`: zero-content correlation-file skip. Two-layer fix: UI's `_correlation_blob_is_degenerate` in `micgen_input_service.py` detects all-zero BLOBs (e.g. `cement151.k2o` for the K2O-free cement151) and skips writing so micgen's existing missing-file handler kicks in; micgen.c `rand3d` also gained a `fabs(sdiff) < 1e-12` guard returning error code 4 instead of segfaulting. Same class as S39 divide-by-zero; latent on macOS too. (iii) Superproject `54e02b71` + `238389b5`: bump to `1.0.0-alpha.2.1` for NIST hotfix installer + rename installer filename to include version. **Distribution status:** `THAMES-1.0.0-alpha.2.1-win64-setup.exe` (599 MB) uploaded as additional asset to the alpha-2 GH release page (tag unchanged); AppId matches alpha-2's GUID so testers upgrade in place preserving data. Two end-to-end verifications on Windows: cem152-fa direct-thames path (672 h, 1956 cycles, 332 clamp warnings, exit 0) and cem151-fa-1 full-UI flow (672 h, 2363 cycles, 71 clamp warnings, exit 0). POST_ALPHA: phase connectivity calculator returns erroneous results (Jeff-observed, deferred).

### Session 63 (Aug 25, 2026): mac verification of the S61+S62 fix bundle + dead migration wire-up found and fixed

Single-focus mac session. Full narrative: `docs/session63_summary.md`. Commit `fbb87b60`.

- **Verification of all six fix-bundle items on macOS.** Rebuilt `bin/thames` + `bin/micgen` from freshly-synced submodule (`6f40f4a`). Static reads confirmed clamp region, `rand3d` `sdiff` guard, migration function, and zero-BLOB skip logic all present. Dynamic tests via Jeff's UI: Step 4 (cem151-fa-1 microstructure gen) completed with `cement151.k2o` absent from op folder and the exact S62 skip-message text in `thames.log`; Step 5 (HY-cem151-fa1-1 hydration, 672 h) completed in 4589 cycles / 2.0 min wall clock with 216 DC-depletion clamp warnings and provenance sidecar showing `exit_code=0`, `success: true`, matching submodule `git_hash: 6f40f4ac`, DCH sha256 confirming the C3S/C3A/glass-corrected DCH. Cycle count higher than Windows's 2363 (double-precision arithmetic ordering + adaptive stepper making different micro-decisions), same 100% success rate — not a regression. **All six fixes verified working on Mac.**

- **Dead migration wire-up discovered and fixed.** DB inspection showed `20260824_01_glass_phase_am_rename` was NOT applied on Jeff's Mac DB (latest applied still `20250906_001` from Sep 2025), and `material_phase` still held bare `CA2S` + `CAS2` for ClassF-FlyAsh. Grep confirmed the cause: `MigrationManager.upgrade_database()` has **zero live callers anywhere in the app** — the only references are the definition itself, an `__init__.py` re-export, and the `create_migration_manager` factory. Neither `ServiceContainer.__init__` nor `DatabaseService.initialize_database()` invoked the migration manager. The S61 commit message claimed the migration "runs at app launch" but this claim was false in the current codebase. The Windows S62 verification worked either through a fresh install (installer wrote post-S59 seed DB with (am) names already) or via some other path — but any Windows NIST tester upgrading in-place (installer preserves data) still has the latent Bug A. **Track 1** (manual SQL) unblocked today's mac test by applying the rename + inserting the migration row into Jeff's DB. **Track 2** (`fbb87b60`): added a `create_migration_manager(self.db_service).upgrade_database()` call to `ServiceContainer.__init__` immediately after `self.database_service = self.db_service`; wrapped in try/except so migration failure logs an error but keeps the app launchable. Verified by running `python -c "from app.services.service_container import ServiceContainer; ServiceContainer()"` from a fresh interpreter — six-migration enumeration appears in the log, glass-phase entry recognized as already applied.

- **POST_ALPHA class-of-bug entry added (`fbb87b60`).** "Startup migration wire-up: no test guards the 'does `upgrade_database()` actually get called?' invariant." Proposes (a) a startup smoke test that instantiates `ServiceContainer()` on an empty temp DB and asserts expected migrations reach it, and (b) the registry-driven migration loop already suggested in S61's "Phase renames require matching DB migration" item. The point fix is LANDED but the class of bug remains open until one of those lands. Cross-references the LANDED S61 item.

- **Mac hotfix decision: DEFERRED to alpha-3.** Distributed `THAMES-1.0.0-alpha.2-macOS.zip` (S45, May 2026) is now stale enough that six severe or moderate bugs latent in it (fly-ash abort, cement151 SIGSEGV, ClassF-FlyAsh Bug A, Mix Design 32³ silent-failure, silica-fume oscillation, kinetic-editor save no-op) would need addressing. Jeff confirmed no known mac tester currently on alpha-2. Alpha-3 will bundle S46-S63's substantive work across both platforms.

- **NIST tester Windows implication (open).** With Track 2 landed, any Windows NIST tester who took the source-rebuild distribution path picks up the wire-up fix on next `git pull`. Testers who took the installer path may have latent bare glass names in their DB (in-place upgrade preserves data). If they report Bug A on a ClassF-FlyAsh mix, respond with the manual SQL snippet — smallest surface, no repackage needed. Otherwise the fix silently reaches them via alpha-3.

---

## PRIORITY TASKS

### 1. Adaptive Time Stepping (COMPLETE)
AdaptiveTimeController + GEMS convergence accessors + kinetics-based initial timestep + UI configuration (7 SpinButtons) + simparams.json. Defaults dt_initial=0.001h, dt_max=4h, growth_factor=1.5, successes_for_growth=2. See `docs/adaptive_timestepping_implementation_plan.md`.

### 2. GEMS Error Recovery (COMPLETE)
IC depletion recovery with charge compensation, IC_FLOOR=1e-5 (must NOT exceed), runtime electrolyte concentration safety, exit_status.json + UI alerts, concentration_overrides.json.

### 3. Documentation (MOSTLY COMPLETE)
User Manual at `docs/USER_MANUAL.md` (~1,200 lines) with 26 screenshots. 2 screenshots still missing (elastic results, workflow1 results).

### 4. Known Issues
- UI memory bloat: Loading 200³ microstructures causes ~5.9 GB RAM usage
- Windows process termination: UI "stop and delete" may not fully kill thames.exe
- micgen exit segfault during `freemicgen()` cleanup (after output written, low priority)
- Near-depletion phases can collapse adaptive timestep at late ages
- Reconciler flips live child operations to CANCELLED on UI restart (persist child PID at launch)
- Silent Pydantic validation failures in Mix Design auto-save

### 5. Post-Alpha TODO List
Deferred improvements are tracked in `docs/POST_ALPHA_TODOS.md`. Append there whenever a "later" / "post-alpha" / "not blocking alpha" item comes up in conversation; do NOT add post-alpha items directly to this file.

---

## Immutable Materials

38 materials are immutable (read-only, migrated from VCCTL): all materials beginning with "cement", csatype10, csatype50, danwhite, dh, frcement, ma157, ma160, ma165, ma178, rossi, sacci-425, sacement, ustype1, NormalLimestone.

---

## MANDATORY: Cross-Platform Safety Protocol

**CRITICAL: Before making ANY change to these files, ALWAYS check both platforms:**
- `.spec` files (`thames-windows.spec` is now the canonical cross-platform spec; `thames-macos.spec` was deleted in S45)
- Path-related code (`directories_service.py`, `config_manager.py`, `app_info.py`)
- Build scripts (`build-macos.sh`, `build-windows.sh`)
- Hooks directory

**Required checks for EVERY change:**

1. Read BOTH platform code paths (`grep -n "pattern" thames-windows.spec` and check IS_MACOS/IS_WINDOWS branches).
2. **State explicitly BEFORE making the change:**
   - "This change affects: [macOS / Windows / both]"
   - "Windows currently does: [X]"; "macOS currently does: [Y]"; "After this change: [Z]"
   - "This will/won't break Windows because: [reason]"
3. For path changes: verify where files are bundled AND where code looks for them on BOTH platforms.

**Failure to follow this protocol causes platform regressions and wastes user time.**

---

## Git commands
- Do not run a git command unless requested.
- Use `git add -A` to stage.
- ALWAYS include both co-authors in commit messages:
  - `Co-Authored-By: Jeffrey W. Bullard <jwbullard@tamu.edu>`
  - `Co-Authored-By: Claude <noreply@anthropic.com>`
- **CNT/JMAK/transport work: Jeff drives all git operations.** Submodule push first, then super-repo pointer bump.

## Responses
- Do not use "You're absolutely right!". Instead use "Good point." or "I see what you are saying."

---

## OS Switching Procedures (CRITICAL - READ FIRST)

When working across Mac/Windows/Linux, use these scripts to keep the git repo synchronized:

### Starting Work on Different OS
```bash
./pre-session-sync.sh
```
Fetches, shows incoming commits, creates a backup branch, pulls with rebase, verifies. Use ALWAYS at start of session on different OS.

### Ending Work Session
```bash
./post-session-sync.sh
```
Shows uncommitted changes, prompts for message, `git add -A`, commits with standard format, pushes to remote. Use ALWAYS at end of work session.

---

## Key Technical Patterns

### PyInstaller Path Resolution
```python
# WRONG - breaks in PyInstaller:
project_root = Path(__file__).parent.parent.parent
# RIGHT - use service abstraction:
operations_dir = self.service_container.directories_service.get_operations_path()
```

### Platform-Specific subprocess
```python
popen_kwargs = {'stdout': ..., 'stderr': ...}
if sys.platform == 'win32':
    popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
process = subprocess.Popen(cmd, **popen_kwargs)
```

### Cross-Platform User Data Directories
- **macOS:** `~/Library/Application Support/THAMES/`
- **Windows:** `%LOCALAPPDATA%\THAMES\`
- **Linux:** `~/.local/share/THAMES/`

### Threading discipline (S44)
Widget mutation from a non-main thread on Windows causes silent heap corruption + Heap-Terminate-on-Corruption fastfail. Use `src/app/utils/thread_safety.py::assert_main_thread()` at entry points of widget-touching methods; BG threads must go through `GLib.idle_add`.

### THAMES per-100-g normalized frame (S53)
`DCMoles_[]`, `microPhaseMass_[]`, `microPhaseVolume_[]`, and `KineticModel::scaledMass_` are stored in a normalized "per 100 g of total solid" frame (established by `Lattice::normalizePhaseMasses`). **Consult before combining with physical `getVolumePerVoxel`/`getDCMolarVolume`** — off by ~10⁷× cost us Session 53. See memory `reference_thames_per100g_convention.md`.

### Phase IDs must be contiguous 0..N-1 (S55)
Phase IDs are used as array indices; gaps cause `microPhaseMass_ contains N elements, but tried to access element K` crashes. Not documented anywhere. POST_ALPHA TODO candidate.

---

# Important Instructions
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

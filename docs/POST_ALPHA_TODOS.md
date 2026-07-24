# THAMES Post-Alpha TODO List

This file tracks improvements, fixes, and design decisions that were identified during alpha development but are **deferred until after the alpha release** to avoid scope creep.

Add new items at the bottom with date, short title, context, and proposed fix. Strike-through or remove items only after they're implemented and verified in a release.

---

## Open Items

### Adaptive timestep: near-depletion phase causes kinetics-constraint stall

**Identified:** 2026-04-21 (Session 41, ccr152-concrete 28-day hydration)

**Symptom.** At late ages (~9 days in a ccr152 concrete mix), the adaptive timestep collapsed to ~0.06 ms per cycle, advancing simulated time by only 36 seconds per 178 cycles. The run would have required weeks of wall-clock time to reach 28 days.

**Root cause.** `Controller.cc::computeKineticsBasedMaxTimestep()` limits the timestep so that no DC's moles change by more than `maxRelativeChange_` (default 5%) per step. For phases near exhaustion (Arcanite at 2 voxels out of 8 million), 5% of a tiny mole count is essentially zero, so the allowed timestep collapses even though the actual kinetic rate is small. The constraint's denominator, not the rate, is the pathology.

**Proposed fix.** Add a volume-fraction (or voxel-count) threshold inside `computeKineticsBasedMaxTimestep`: skip phases whose current volume fraction is below some floor (e.g., `1e-5`, or equivalently < 10 voxels for a 200³ microstructure) when computing the minimum-rate constraint. Preserves the kinetics safety net for normally-populated phases while ignoring near-exhausted ones that distort it.

**Alternative** (more invasive): when a phase drops below N voxels and is monotonically decreasing, dissolve its remainder in a single step and mark it suppressed for the rest of the simulation.

**Files.** `backend/thames-hydration/src/thameslib/KineticController.cc` (or wherever `computeKineticsBasedMaxTimestep` is defined), `Controller.cc` for any integration changes.

**Workarounds available during alpha.**
- Suppress Arcanite / Thenardite / Bassanite / Anhydrite via the Hydration Products tree before launching a long run (loses explicit sulfate-release tracking but avoids the stall).
- Disable adaptive time stepping and use dense output spacing (hourly) so the fixed timestep stays GEMS-safe.

---

### Micgen exit segfault during freemicgen() cleanup

**Identified:** 2026-03-19 (Session 33)

**Symptom.** After microstructure output is successfully written, `micgen.c` segfaults during `freemicgen()` exit cleanup.

**Impact.** Low — all outputs are written before the crash, so results are intact. However, the non-zero exit code confuses some callers and may alarm alpha testers.

**Proposed fix.** Review `freemicgen()` for use-after-free or double-free patterns. Possibly related to the `static`-allocation fix in Session 33 that changed lifetime semantics.

---

### Windows: UI "stop and delete" may not fully kill thames.exe

**Identified:** Noted as a known issue in CLAUDE.md (pre-alpha).

**Symptom.** On Windows, clicking "Stop and Delete" in Operations may leave `thames.exe` running as a zombie process.

**Proposed fix.** Use `taskkill /T` (tree-kill) on Windows to terminate child processes, or `psutil.Process.children(recursive=True)` before calling `terminate()`.

---

### UI memory bloat loading 200³ microstructures

**Identified:** Noted as a known issue in CLAUDE.md (pre-alpha).

**Symptom.** Opening a 200³ microstructure in the 3D viewer consumes ~5.9 GB RAM; the manual's "Memory considerations" table (100 MB / 350 MB / 800 MB / 2.7 GB for 100/150/200/300³) underestimates by ~7× for the 200³ case.

**Proposed fix.** Profile the VTK pipeline; likely candidates are redundant per-voxel allocations, uncompressed color/phase arrays, or unreleased copies in the Python-VTK bridge. May want to switch to `vtkImageData` with point-data arrays rather than per-voxel cells.

---

### Reconciler marks live operations CANCELLED when UI is restarted

**Identified:** 2026-04-23 (Windows alpha smoke-test session)

**Symptom.** When the THAMES UI process (`python.exe`) is killed or crashes while a child operation (e.g. `micgen.exe`, `thames.exe`) is still running, the next UI launch flips that operation's DB row from `RUNNING` to `CANCELLED` — even though the child process is alive and continues to write output. The user, seeing "Cancelled," deletes the operation; the DB row is removed but the on-disk operation folder is left behind, and the still-running child process eventually finishes work that nobody is tracking.

**Root cause.** The Session 41 reconciliation in `operations_monitoring_panel.py::_load_operations_from_database` was designed for the case where the UI was killed cleanly *with no surviving children*: any `RUNNING` row with no live process must be stale. The check is "is the original UI-tracked PID alive?" — but child processes spawned by the previous UI process have a different PID and are not tracked across UI restarts. So a live grandchild looks identical to a crashed operation.

**Proposed fix.** Persist the *child* PID (the spawned process, not the UI's own PID) in the operations DB row at launch time, plus enough identification (image name, working dir, start time) to reattach across UI restarts. On startup reconciliation: if any of those identifiers still match a live process, leave the row as `RUNNING` and re-attach the monitor; only flip to `CANCELLED` when no matching process can be found. On Windows use `psutil.process_iter(['pid','name','cwd','create_time'])`; on POSIX, the same `psutil` call is fine.

**Secondary fix.** When the user deletes a `CANCELLED`/`FAILED` operation from the Operations panel, either (a) delete the on-disk folder too, or (b) check `psutil` first and warn if a process with that working directory is still alive. Otherwise live-but-untracked processes silently keep writing to a directory the user thought was gone.

**Workarounds available during alpha.** After UI crash/restart, before deleting any "Cancelled" operation, check Task Manager / `tasklist` for live `micgen.exe`/`thames.exe`. If found, let them finish and treat the result folder as authoritative.

---

### Materials Panel: delete sometimes silently fails for user-created materials

**Identified:** 2026-04-27 (Windows alpha-2 testing)

**Symptom.** A user-created material (`Clinker152`) could not be deleted via the Materials Panel UI. Clicking Delete appeared to do nothing — no error, no prompt, no row removal. The material had no foreign-key references and was not flagged immutable in the database, so direct SQL deletion succeeded immediately.

**Root cause (suspected, not yet confirmed).** The deletion code path in `materials_panel.py` likely guards on `immutable` OR on a `is_clinker`/`has_clinker` heuristic and silently no-ops if a condition is met. `Clinker152` has `is_clinker=0, has_clinker=1` which may trip a stale check. Alternatively the delete handler may dispatch by tag (the `material_tags` table) and silently skip unfamiliar tags.

**Proposed fix.** Walk the delete path: `_delete_material` → `_get_material_type` → tag lookup. Either (a) make the check authoritative via the `immutable` column only, or (b) when a delete is silently refused, raise a visible dialog explaining why. Today the user has no way to tell that a click did nothing.

**Workarounds available during alpha.** Direct SQL on `%LOCALAPPDATA%\THAMES\database\thames.db`:
```sql
DELETE FROM material WHERE name='<material-name>';
```
Always backup the database first.

---

### Load-from-Previous: microstructure-resident phases missing from hydration product tree

**Identified:** 2026-05-11 (mid-day diagnostic on `HY-ccr152-sf15-ws45-01`).

**Symptom.** When the Hydration panel's "Load from previous operation" populates state from a prior op's `_hydration_config.json`, the hydration product tree is missing all phases that were in the original microstructure (Alite, Belite, Aluminate, Ferrite, Anhydrite, Bassanite, Gypsum, Portlandite, …). The list starts at C-S-H. New, non-micro hydration products are loaded correctly.

**Root cause (suspected, not yet confirmed).** The previous-op config replay path likely repopulates the tree directly from `_hydration_config.json`'s phase list, which serializes only the toggled hydration products and treats "microstructure-resident, always selected" phases as implicit. The repopulation skips the implicit-side path. Alternatively the replay path may filter out `is_from_microstructure=True` rows on purpose under the (now obsolete) assumption that they're not user-editable.

**Proposed fix.** When loading from a previous operation, run the same microstructure-scan code used by "New simulation" to seed the tree with micro-resident phases first, then overlay the saved hydration product selections on top. The micro scan reads phases from the `.img` file (or from `_phase_mapping.json` in the op folder, which has the same info).

**Workarounds available during alpha.** Load the microstructure file manually via the file chooser; the tree will populate with both micro phases and the kinetic-product defaults. Then individually re-toggle any non-default selections.

---

### Load-from-Previous: microstructure field not populated, "no microstructure specified" on run

**Identified:** 2026-05-11 (mid-day diagnostic on `HY-ccr152-sf15-ws45-01`).

**Symptom.** After "Load from previous operation" repopulates the Hydration panel, clicking Run errors with "did not specify a microstructure" or similar. The microstructure file path widget appears empty even though the previous op's config recorded it.

**Root cause (suspected).** The microstructure path is likely keyed by absolute path in `_hydration_config.json`. If the replay path attempts to set the file-chooser widget by absolute path and the path no longer resolves (or the widget's setter is async/no-op without the file existing in the dialog's last-visited folder), the field silently stays empty. Alternatively, a clear-on-load reset wipes the field after replay.

**Proposed fix.** In the load-from-previous handler, after replaying the config, explicitly set the microstructure path widget from the recorded value AND verify the file exists. If the file is missing, surface a dialog rather than silently leaving the field empty.

**Workarounds available during alpha.** After loading from previous, manually re-select the microstructure file via the file chooser before running.

---

### Suppression toggle for microstructure-resident phases: replace silent allow with confirmation dialog

**Identified:** 2026-05-11 (mid-day patch to `hydration_product_selector.py`).

**Context.** Originally, the hydration product tree's `_checkbox_cell_data_func` made microstructure-resident phases (`is_from_micro=True`) non-activatable and the toggle handler rejected such clicks with a debug log. This was footgun protection (preventing accidental suppression of, say, Alite which would invalidate the cement composition). The protection was relaxed today because it blocked the documented workaround for the near-depletion adaptive-timestep stall (suppressing Arcanite/Thenardite). Current behavior: any phase row is toggleable, with an info log noting that initial voxels will dissolve once and not regrow.

**Risk.** Users can now silently suppress major clinker phases (Alite, Belite, etc.) and the simulation will proceed with the entire cement composition gutted. No dialog, no warning beyond the info log.

**Proposed fix.** For beta, replace the relaxed gate with a confirmation dialog when toggling OFF an `is_from_micro` phase: "{Phase} has {N} voxels in the initial microstructure. Suppressing means these will dissolve once and not re-precipitate. For minor sulfate phases (Arcanite, Thenardite, etc.) this is a documented workaround; for major clinker phases (Alite, Belite, Aluminate, Ferrite) this will invalidate the cement composition. Continue?" Default to Cancel. This keeps the workaround accessible without re-introducing the silent footgun.

**Files.** `src/app/widgets/hydration_product_selector.py` (the `_checkbox_cell_data_func` and `_on_product_toggled` paths).

---

### Kinetic editor: "Thermodynamic" selection silently discarded when phase already has kinetic parameters

**Identified:** 2026-05-11 (mid-day diagnostic on `HY-ccr152-sf15-ws45-01`). Being addressed in-session.

**Symptom.** User opens the per-phase kinetic editor for Portlandite, switches the model type from "Standard" (the default seeded value) to "Thermodynamic", clicks Apply/OK. The dialog visually shows Thermodynamic selected. But the run's `*_hydration_config.json` saves the full Standard schema (`type: "Standard"` plus `dissolutionRateConst`, `dorexp`, etc.) and the `simparams.json` writer dutifully emits a `kinetic_data` block — so the C++ controller treats Portlandite as kinetically-bounded Standard, not as a Thermodynamic equilibrium phase. This caused a multi-hour stuck-at-cycle-11 stall in the user's ccr152+silica-fume hydration: the kinetics constraint was clipping `dt` to ~1e-5 h whenever GEMS demanded a large Portlandite step.

**Root cause (suspected).** The kinetic-editor dialog populates a "Standard" parameter form when opened (default), the user changes only the radio/dropdown to "Thermodynamic", and on Apply the code reads back the full form (still populated with the seed Standard params) instead of branching on the type and emitting only `{"type": "Thermodynamic"}`. The other Thermodynamic phases in the same config (Arcanite, Thenardite) were probably set on a CLEAN dialog with no prior kinetic params — so the form was empty and the Apply emitted the minimal dict.

**Proposed fix.** In the kinetic-editor's Apply handler, branch on the selected type FIRST:
- `Thermodynamic` → emit `{"type": "Thermodynamic"}` (drop all rate/exp fields).
- `ParrotKilloh` → emit only PK fields (`k1, k2, k3, n1, n3, dorHcoeff, activationEnergy, loi`).
- `Standard` → emit the Standard schema.
- `Pozzolanic` → emit Pozzolanic schema.

The same coercion should happen on `simparams.json` generation (`hydration_input_service.py::generate_simparams`) as a defense-in-depth so a Thermodynamic phase never receives a residual `kinetic_data` block from the saved config.

**Workarounds available during alpha.** After running, manually edit `simparams.json` to delete the `kinetic_data` key from the affected phase's entry under `microstructure.phases[]`. Re-launch the C++ binary directly (`bin/thames -o Result < input.in` from inside the operation directory) — the UI rewrites simparams every relaunch, so the workaround must be applied between simparams write and binary launch.

---

### Known stall pattern: GEMS-Portlandite oscillation in cement+silica-fume systems

**Identified:** 2026-05-11 (root-causing `HY-ccr152-sf15-ws45-01`).

**Symptom.** A binder with cement + silica fume gets stuck at an early cycle (cycle ~11 in a ccr152-sf15 example) with these signatures: dt clipped to ~1e-5 h, `currTime` advancing by < 1e-4 h per cycle, repeated `checkICMoles: IC Ca depleted to -0.5 mol` followed by 0.5-mol Ca injections, and `Lattice::changeMicrostructure` proposing wildly oscillating Portlandite mass between cycles (e.g. 0 → 246k → 104k → +2.2M voxels in three successive cycles). The same cement WITHOUT silica fume runs cleanly to cycle 1000+.

**Root cause.** Silica fume introduces alternative C-S-H formation pathways that change the Ca/Si phase landscape. GEMS finds two near-degenerate solid distributions; on each `recall GEM` (triggered by IC depletion or lattice anormal-end), GEMS flips between them. Portlandite is the proximate beneficiary/victim of each flip. If Portlandite has a Standard kinetic model, the `maxRelativeChange=5%` constraint clips `dt` to absorb the proposed Portlandite step, but doesn't prevent the oscillation — every cycle proposes a different solid distribution. Result: the kinetics constraint locks the simulation while GEMS spins.

**Proposed fix.** Likely two parts:
1. **Backend** (`Controller.cc::computeKineticsBasedMaxTimestep` or related): when consecutive cycles show alternating-sign mole changes for the same secondary product (sign-flip on Portlandite ΔN between cycles), treat the system as oscillating and either let one big step land OR fall through to dt_max with a warning. Detecting the flip is straightforward; deciding the right action is the design question.
2. **Material defaults**: for Portlandite (and similar fast-equilibrium products with the same character — ettringite-AFm, perhaps), the default kinetic model in the materials DB should be "Thermodynamic" rather than "Standard". Standard is appropriate only when the user explicitly wants to model nucleation/dissolution kinetics for that phase.

**Workarounds available during alpha.** Set Portlandite to Thermodynamic in the kinetic editor BEFORE first run (or via direct simparams.json edit — delete the `kinetic_data` block from the Portlandite phase entry). Verified on `HY-ccr152-sf15-ws45-01` to clear the stall: cycle 11 → 19 in ~3 min, dt grew 0.0072 → 0.012 h, zero Ca depletion events, smooth monotonic Portlandite growth. **Note**: this interacts with the kinetic-editor save bug above — even if you select Thermodynamic in the UI, you may need to verify the saved config or apply the manual workaround until the save bug is fixed.

---

### Lattice-trapped phase blocks GEMS at later ages (encapsulated-remnant stall)

**Identified:** 2026-06-04 (root-causing `HY-ccr152-sf15-ws45-04`, cement + 15% silica fume).

**Symptom.** A run that has reached late age (sim time 305.86 h ≈ 12.7 d in this example) and a healthy adaptive timestep (dt grew to 4 h before the cliff) suddenly clips dt to the 1e-5 h floor on every cycle and eventually exits via `GEMS solver exceeded maximum consecutive failures` (50 failures in a row). Wall time was ~4.7 h, total cycles 2719 with 2654 ok / 65 failed (97.6% success rate up to the cliff). `Result/exit_status.json` is written cleanly so the failure is detected, not silent.

The log signature, starting ~80 cycles before termination, is identical on every cycle:

```
DISS_INI for ettr : count_=26  dim_isite=0  numleft=26
WAIT to dissolve 26 voxels ...
anormal end for phases : ettr, numDiff=26
=> recall GEM after (re)setDCLowerLimit
...
Kinetics constraint: reducing timestep from 4.000e+00 to 1.000e-05 h
```

At the cliff cycle (2648 in this run), the recall-GEM-with-locked-DCLowerLimit call itself stops converging; every subsequent retry uses identical state at identical `currTime`, so the 50-failure budget drains with zero progress.

**Root cause.** A small number of voxels of a minor late-age phase (here: 26 voxels of ettringite, 3×10⁻⁶ of the total 8M voxel system) become **inaccessible to the dissolution interface** during the AFt → AFm conversion. `count_=26` says they exist; `dim_isite=0` says none of them have any neighbor a dissolution event can be placed on — they have been encapsulated by the surrounding AFm/CSH phases (here: C4AsH14, monosulf-AlFe, C3AH6) and lost contact with porosity or electrolyte. GEMS still demands ettr → 0 because the equilibrium AFt → AFm conversion is in progress at this age. The system's coping path (recall GEMS with `DCLowerLimit = residual ettr moles`, locking the trapped voxels into the GEMS state) works for ~80 cycles but forces `dt → 1e-5 h` every cycle because the kinetic-constraint detector reads the lattice mismatch as a near-depletion signal. Eventually the locked-state GEMS call itself stops converging and the run exits.

Silica fume appears to be the trigger because the extra CSHQ growth (Sfume → CSHQ) and aggressive AFt → AFm reshuffle bury ettringite remnants from outside-in before they finish dissolving. The companion run without silica fume (`HY-ccr152-ws45`) reached 28 days cleanly. The pattern is not unique to ettringite — any phase whose GEMS-equilibrium goes to zero while small encapsulated remnants survive in the lattice should produce the same signature.

**Proposed fix.** Three options, increasing cost:

1. **Lattice sweep when a phase becomes inaccessible** (cheapest backend fix). In `Lattice::dissolvePhase`, when `dim_isite == 0` AND `count_ > 0` AND the count is below a threshold (e.g. `< 1e-5` of total voxels), sweep the residual voxels directly to electrolyte/void and update the DC moles accordingly. This bypasses the interface system entirely for tiny encapsulated remnants. Risk: charge balance — sweeping requires re-balancing IC moles the same way `checkICMoles` does.
2. **Adaptive-timestep oscillation detector**. Add a counter for "consecutive cycles where `dim_isite=0` triggered a GEM recall for the same phase"; after N (e.g. 20) such cycles, treat the phase as effectively-locked, suppress it from the kinetic-constraint denominator (so dt is no longer clipped), and let the simulation continue with the residual voxels frozen in place.
3. **Pre-run heuristic**: when silica fume volume fraction exceeds a threshold (~5%), default ettr (and possibly other AFt phases) to suppressed in the simparams generator, with a UI note. Cheapest UX path but kills early-age realism — ettringite formation in the first hours is a real and important kinetic event for cement chemistry.

Long-term, (1) + (2) together are the right answer; (3) is a workaround for the UI to surface.

**Files.** `backend/thames-hydration/src/thameslib/Lattice.cc` (`dissolvePhase`, `changeMicrostructure`); `backend/thames-hydration/src/thameslib/Controller.cc` (`computeKineticsBasedMaxTimestep`, the kinetic-constraint clipping path); `backend/thames-hydration/src/thameslib/AdaptiveTimeController.{h,cc}` (oscillation-detector state).

**Workarounds available during alpha.** Add the trapped phase to `suppressed_phases` in simparams (via the Hydration Product Selector — uncheck the phase before launching). For cement + silica-fume systems specifically, uncheck `ettr` so GEMS routes sulfate straight to monosulf-AlFe / C4AsH14 from the start with no AFt → AFm transition. The 26 trapped voxels at 12 days are chemically negligible (3×10⁻⁶ of system volume). Alternative workaround: assign the affected phase a slow Pozzolanic kinetic model so it drains gradually instead of GEMS demanding instantaneous full dissolution at conversion time.

---

### Mix Design auto-save: surface Pydantic ValidationError instead of silently failing

**Identified:** 2026-06-04 (Session 47, root-causing the empty `ccr152-ws45-32` orphan folder).

**Symptom.** User entered a system size of 32 in the Mix Design panel and clicked Generate. The operation folder was created at `~/Library/Application Support/THAMES/operations/ccr152-ws45-32` but stayed empty: no input file, no `micgen` launch, no error dialog, no toast, no status-bar message. From the user's perspective the click did nothing. The only evidence was a buried `❌ Error auto-saving mix design` line in `thames.log` showing a Pydantic `ValidationError` with `Input should be greater than or equal to 50` for `system_size`. (The schema constraint itself was also wrong — a stale `ge=50` on the legacy `system_size` field while the per-axis `system_size_x/y/z` allow `ge=25`. That part was fixed in-session by relaxing `mix_design.py:154` and `:255` to `ge=25, le=400` to match the per-axis bounds.)

**Root cause.** `MixDesignPanel._auto_save_mix_design_before_generation` (around `mix_design_panel.py:5628`) wraps the `MixDesignCreate(**data)` call in a broad `try/except` that logs the traceback and returns `None`. The caller in `_generate_microstructure_input` (or equivalent) checks for `None` and logs `No saved mix design ID - cannot generate input file` — and then **just returns**. No `MessageDialog`, no status update. The empty folder was created earlier in the flow (the `Created mix folder` log line precedes the validation), so the failure also leaves orphan directories that have to be cleaned up via Sync with Filesystem.

This pattern (catch → log → return None → silently abort) is the same shape as Bug 2 from Session 44 (orphan widget calls from a background thread). Both expose the same underlying issue: errors that should be user-visible are being demoted to log noise.

**Proposed fix.** In `_auto_save_mix_design_before_generation`, distinguish `pydantic.ValidationError` from other exceptions. For the ValidationError path:

1. Pretty-format `e.errors()` into a human-readable list (`field` → `msg`).
2. Show a `Gtk.MessageDialog(MessageType.ERROR)` with the list of failing fields, parent set to the panel's toplevel window.
3. Still return `None` so the caller aborts — but the user knows why.

For the unexpected-exception path, keep the current log-and-return behavior but also pop a "An unexpected error occurred — see the log file at ~/Library/Application Support/THAMES/logs/thames.log" dialog. Silent failure is the bigger UX bug than the specific schema rejection.

**Defense in depth.** Also do not create the operation folder until after auto-save succeeds. Current order: create folder → extract data → validate → fail. Better order: extract data → validate → create folder → write input file. Eliminates the empty-orphan-folder side effect entirely.

**Files.** `src/app/windows/panels/mix_design_panel.py` (`_auto_save_mix_design_before_generation` and its caller; also the folder-creation order).

**Workarounds available during alpha.** If a microstructure generation "does nothing," check `~/Library/Application Support/THAMES/logs/thames.log` for a `❌ Error auto-saving mix design` line near the end. The Pydantic message identifies the offending field. On Windows, the log path is `%LOCALAPPDATA%\THAMES\logs\thames.log`.

---

### Site-saturation gating for heterogeneous CNT (θ < 180°)

**Identified:** 2026-07-23 (Session 51, CNT integration Step 7 correction).

**Context.** The CNT rate calculation currently returns a fractional voxel count whenever `nucleation_.has_value()` and `S > 1`, symmetrically for `StandardKineticModel` and `PozzolanicModel`. This is physically correct for **homogeneous** nucleation (θ = 180°): every electrolyte voxel is a valid site, so the "site saturation" regime (nucleation blocked because sites are scarce) never engages in practice.

For **heterogeneous** nucleation (θ < 180°) — planned for C-S-H, ettringite, and other later phases — nuclei form only on scarce substrate voxels. In that regime the available site count is a genuine physical constraint that must limit the CNT rate, otherwise the model over-produces nuclei at high S.

**Proposed fix.** When heterogeneous CNT is added, extend `computeNucleationVoxels` (both Standard and Pozzolanic paths) to divide by an available-substrate-voxel count and cap the fractional-voxel result when that count is small. Implementation depends on which phase's substrate is being sampled and how substrate voxels are identified; probably a lookup into `Lattice::count_[substrateID]` gated by the `theta_deg` parameter in `NucleationParameters`.

**Files.** `backend/thames-hydration/src/thameslib/StandardKineticModel.cc`, `PozzolanicModel.cc`, possibly `NucleationRate.h/.cc` if the gating math is factored out.

**Not blocking alpha.** No θ<180° phase is enabled by default; homogeneous portlandite nucleation is the only Step-6-configured example.

---

### Refactor Lattice::changeMicrostructure into extracted helpers

**Identified:** 2026-07-24 (Session 51, backend audit sweep).

**Context.** `Lattice::changeMicrostructure` (Lattice.cc:3676–4534, 859 lines in a single function body) is the microstructure-update workhorse called every cycle after GEMS equilibration. Its original author's own `@todo` at Lattice.cc:3720 says "This function is very large; consider breaking it into small pieces for ease of maintenance and readability." First-year grad students consistently get stuck here first — it's the widest single-method complexity in the backend.

The function has clearly-separable responsibilities that can each become a private method. A skim of the current body identifies at least seven blocks:

1. **Bookkeeping / recall accounting** (lines ~3682–3717): argument handling, recall-cycle diff vector cleanup, static call counting, porosity vector refresh from ChemicalSystem.
2. **Load target state from ChemicalSystem** (~3717–3780): reads target volume fractions and phase names, calls `adjustMicrostructureVolumes`, logs before/after volumes.
3. **Compute per-phase target voxel counts** (~3809–3838): converts target volumes to integer voxel counts (`netsites` deltas).
4. **Sulfate-attack transformation branch** (~3839–4132, ~293 lines): huge conditional block that only runs when `simtype == SULFATE_ATTACK` and `time > sulfateAttackTime_`. Handles molar-volume ratios for phase transformations, crystallization-pressure calculations, and post-transformation microstructure updates. Two existing `@todo` markers inside note "Find out why we need to do all of this just because there will eventually be sulfate attack" — a clear signal this block deserves its own function AND its own audit.
5. **Standard normalization branch** (~4133–4193): the `else` for non-sulfate-attack cycles, computes voxel counts from normalized volume fractions.
6. **Partition into dissolve vs grow lists** (~4194–4220): iterates from `FIRST_SOLID`, splits phase IDs into two vectors based on `netsites` sign. An existing `@todo` at line 4224 notes "Consider making the starting index more general."
7. **Grow-list ordering + dissolve/grow execution** (~4220–4285 dissolve, ~4285–end grow): calls `dissolvePhase()` and `growPhase()` in turn, with GEMS-recall bookkeeping if either fails.

**Proposed fix.** Extract each block into a private method with a descriptive name and clear inputs/outputs. Candidate signatures:

```cpp
// bookkeeping / recall accounting
void trackChangeMicrostructureCall(int recalls,
                                   const vector<int> &vectPhIdDiff,
                                   const vector<int> &vectPhNumDiff);

// target-state ingestion
void loadTargetVolumesFromChemSys(vector<double> &vol_next,
                                  vector<string> &phasenames,
                                  int cyc);

// integer voxel-count computation
void computeNetVoxelCounts(const vector<double> &vol_next,
                           vector<int> &netsites);

// sulfate-attack path (large; probably breaks further into 3–4 sub-methods)
int handleSulfateAttackTransformation(double time, int cyc, ...);

// dissolve/grow partitioning
void partitionPhasesByNetChange(const vector<int> &netsites,
                                vector<int> &dissPhaseIDVect,
                                vector<int> &growPhaseIDVect);

// execution (or two methods, one per direction)
int executeDissolutions(vector<int> &dissPhaseIDVect, ...);
int executeGrowths(vector<int> &growPhaseIDVect, ...);
```

`changeMicrostructure` itself then becomes an orchestrator: ~40 lines of numbered calls to the extracted methods, each with a one-line comment saying what stage it represents.

**Constraints and validation.** This is a behavior-preserving refactor. No observable simulation output should change. The verification pattern from the CNT integration (§7 in `docs/CNT_ARCHITECTURE.md`) applies:

- Standalone math tests (already in place) must stay green.
- CNT-off byte-parity: rerun `HY-ccr152-ws45` (Portland) and diff every CSV column against a pre-refactor baseline; expect 100% identity for the first 20 cycles minimum.
- Sulfate-attack path: rerun one archived sulfate-attack config end-to-end (e.g. from the Session-31/32 SA test set) and diff outputs. This is critical because the SA block is the largest extracted piece and the least frequently exercised.

**Suggested sequencing.** Do the extraction in this order to keep each PR reviewable:

1. Extract blocks 1–3 (bookkeeping, target-state ingestion, netsite computation). Small, low-risk. Verify byte-parity.
2. Extract block 6 (partitioning) and blocks 5+7 (normalization + execution). Medium risk; touches the hot path. Verify byte-parity.
3. Extract block 4 (sulfate-attack transformation). Largest and least-familiar block; may require breaking further into sub-methods once the code is isolated. Verify against a real SA config.

**Files.** `backend/thames-hydration/src/thameslib/Lattice.h` (new private method declarations) and `Lattice.cc` (extraction body). No other files touched unless the extracted methods need to become public.

**Why this is worth doing.** Beyond readability, the extracted methods become unit-testable in isolation. The sulfate-attack block in particular carries known design debt (per the existing `@todo` markers) that is invisible while it's buried inside a 859-line function. Extracting it makes the debt actionable.

---

### Backend documentation gaps (systemic)

**Identified:** 2026-07-24 (Session 51, backend audit sweep).

**Context.** A systematic pass through `backend/thames-hydration/src/thameslib/` fixed obvious misleading docstrings (Standard/Pozzolanic model @briefs, `KineticModel` "not used" claim), added rationale to a handful of magic numbers (`stepTimeTHR_`, `elemTimeInterval`, `corPorCSHQ`, `seedRNG`), and added lifecycle notes to `Site::visit_` and cross-references to `docs/CNT_ARCHITECTURE.md`. Larger structural gaps were flagged for later:

1. **`Lattice::changeMicrostructure`** — Refactor tracked as its own dedicated entry below ("Refactor Lattice::changeMicrostructure into extracted helpers").
2. **Phase-ID conventions** are scattered across `global.h` (VOIDID, ELECTROLYTEID, FIRST_SOLID, clinker IDs), `Site.h` (isPorousSolid boundary check), and `Lattice.cc` (many bare integer comparisons). Belongs in a `docs/PHASE_IDS.md` reference document with the ordering convention documented once, cross-referenced from the code.
3. **`Exceptions.h`** — every class here follows the same shape and would benefit from a shared base class; noted in the file docstring.
4. **`RanGen`** — RNG state is process-global via `ran3.cc` statics. Warning added to `ran3.cc` header block; if THAMES is ever parallelized this must be replaced.
5. **`Interface.cc`** — the `Interface` class has hazardous non-owning pointer semantics (constructor takes `Site*` refs whose lifetime it doesn't manage). No fix; noted for a future ownership pass.
6. **`ElasticModel` family** (`ThermalStrain`, `AppliedStrain`) — Voigt-notation index mapping documented once (lines 101-109 in `ElasticModel.h`) but used throughout without reminders; `hasAggregateSlab_` gates ITZ vectors without explanation. Not touched.
7. **`Site.h` position fields** (`inGrowInterfacePos_`, `inDissInterfacePos_`, `inGrowthVectorPos_`, `inDissolutionVectorPos_`) — four fields, subtly different roles, no overview of which is current/stale/updated-when. Not touched.
8. **Legacy commented-out code blocks** — Controller.cc has a large commented-out sulfate-attack path (lines ~1703-1819); Lattice.cc has forward-designed `nucleatePhaseAff` calls commented out at Lattice.cc:1342 and 1701. Not touched (some are intentional design breadcrumbs, some are stale; requires per-block judgment).

**Proposed fix.** Assign each numbered gap above as a stand-alone documentation task. None require code changes to the underlying behavior; each is a targeted comment / docstring / architecture-doc addition. Priority: (1) is highest-value because `Lattice::changeMicrostructure` is where every new grad student will get stuck first.

**Files.** Scattered across `src/thameslib/`. Any doc-only PR should cite this TODO entry so the audit trail is discoverable.

---

### UI support for CNT (nucleation) parameter input

**Identified:** 2026-07-23 (Session 51, CNT integration Step 6).

**Context.** The CNT integration thread added a per-phase `nucleation` sub-block to `kinetic_data` in `simparams.json` (fields `gamma`, `theta`, `A0` — each with `value` / `range` / `provenance` sub-fields per the Session-50 schema decision) plus a top-level `useNucleationKinetics` boolean and `nucleationCapFraction`. The C++ backend fully consumes these; the GTK UI does not yet expose them. Alpha testers who want to enable CNT for a phase have to edit `simparams.json` by hand after the UI generates it.

**Proposed fix.** Extend the Hydration Panel's per-phase kinetic-editor dialog so that when the user selects Standard (or Pozzolanic, once Step 7 lands) as the model type for a phase, an optional "Nucleation" section appears with three parameter widgets (γ, θ, A₀) matching the JSON structure. Add a global switch (checkbox) in the Hydration Panel for `useNucleationKinetics` and a spin-button for `nucleationCapFraction`. Round-trip via the same `simparams_service.py` that already handles suppression state.

**Files.** UI-side: `src/app/windows/panels/thames_hydration_panel.py`, `src/app/widgets/microstructure_phases_editor.py`, `src/app/services/simparams_service.py`, plus preferences persistence.

**Workarounds available during alpha.** Users can hand-edit `simparams.json` in the operation folder before launching a run. Not friendly; documenting the JSON schema in the User Manual would help.

---

### CNT vs. Lattice::changeMicrostructure mass-balance mismatch

**Identified:** 2026-07-24 (SaturatingRateModel Step S4 validation).

**Context.** CNT for Portlandite in `HY-ccr152-ws45-sat-portlandite-cnt` shows the following pattern every cycle once Portlandite SI climbs into the 9–10 range:

1. `computeNucleationVoxels` returns ~1e5 voxels/cycle at S ≈ 10.
2. The adaptive-timestep cap fires and shrinks dt so N_want ≈ N_cap (~92,000 voxels ≈ 1.2 % of lattice).
3. `Lattice::nucleatePhaseRnd` successfully places ~92,000 voxels of Portlandite into random electrolyte sites; `count_[Portlandite]` jumps from ~125 to ~91,800.
4. GEMS runs with `DCLowerLimit == DCUpperLimit == DCMoles_after_placement`, GEMS returns OK.
5. `Lattice::changeMicrostructure` then reports `sites to grow/dissolve: -91,707` for Portlandite — reverting to `newsites: 125`.

Ca-in-solution can only support ~125 voxels of Portlandite; GEMS' `vfrac_next` reflects the mass-balance limit, and `changeMicrostructure` uses vfrac_next rather than DCLowerLimit as its target. Net growth ends up at 2–5 voxels/cycle at SI ~ 10 (stuck), instead of tracking Ca influx smoothly.

The Standard-model Step-6 6b baseline stalled at the same point because Standard's Eq-6 rate law diverges at high S. SaturatingRate replaced that divergent rate law with a saturating one and cleared 6b's dt collapse — the run makes it past the stall — but the CNT+GEMS mass-balance conflict now dominates the throttle. This is orthogonal to the SaturatingRate work.

**Proposed fixes (three, in ascending correctness):**
- **(a) LANDED 2026-07-24 as a guardrail** — CNT cap now accounts for aqueous IC mass availability, not just electrolyte-voxel count. `computeNucleationBasedMaxTimestep` in `KineticController.cc` computes `N_mass_cap = min_over_ICs(aqICMoles[ic] / (vVoxel/vMolar_DC * DCStoich[ic]))` and uses `min(nCap_electrolyte, N_mass_cap)`. Prevents CNT from overshooting when a required IC is legitimately scarce. **Does not resolve the Portlandite-in-Portland-paste symptom** because aqueous Ca in that system (~8.4e-5 mol) supports ~2.8×10⁹ Portlandite voxels — 30,000× larger than the electrolyte cap. The bottleneck there is GEMS's full equilibrium landscape, not raw IC availability.
- **(b)** `Lattice::changeMicrostructure` should treat `DCLowerLimit` as a floor for CNT-placed phases. If GEMS' `vfrac_next` < placed level, either request more IC from the pre-eq loop or short-circuit the removal. **Prerequisite investigation** — see next entry — needs to explain why GEMS returns DCMoles below DCLowerLimit despite the CNT-lock at `KineticController.cc:1492–1493` setting equal upper and lower limits.
- **(c)** Split CNT into "just nucleate a seed, let SaturatingRate do the growth". This is the physical model — CNT gives you a critical nucleus, then the phase grows by ion attachment which the rate law handles. Sub-voxel nuclei would need fractional-voxel bookkeeping (deferred to the transport-kinetics thread).

Option (c) is the eventual right answer. Option (b) is the near-term correct fix once the prerequisite investigation names the mechanism.

**Files.** `backend/thames-hydration/src/thameslib/KineticController.cc` (mass cap landed at `computeNucleationBasedMaxTimestep` ~line 1853), `backend/thames-hydration/src/thameslib/Lattice.cc` (changeMicrostructure — for option (b)), `backend/thames-hydration/src/thameslib/StandardKineticModel.cc` / `SaturatingRateModel.cc` (if the fractional-voxel path is taken for option (c)).

**Workarounds available now.** For alpha, users who enable CNT on a phase whose supersaturation runs far above the calibration onset should expect throttled growth. Portlandite in Portland pastes is the most affected. SaturatingRate without CNT is well-behaved and recommended.

**Evidence.** `~/tmp/thames-satrate-val/comparison.png`, `~/tmp/thames-satrate-val/saturating_rate_validation.md`.

---

### Investigate: GEMS returns DCMoles below DCLowerLimit after CNT-lock

**Identified:** 2026-07-24 (Option-(a) mass-cap follow-up during SaturatingRateModel S4).

**Context.** `KineticController::calculateKineticStep` at lines 1492–1493 raises both `DCLowerLimit` and `DCUpperLimit` to the just-placed `DCMoles_[dcId]` value after every CNT placement. The stated intent (see `docs/CNT_ARCHITECTURE.md` §4) is: prevent GEMS from immediately dissolving the placed nuclei back to the pre-placement floor. GEMS is supposed to be constrained by these bounds.

Nevertheless, in the S4 validation of `HY-ccr152-ws45-sat-portlandite-cnt`, every cycle showed:
- CNT places ~91,796 Portlandite voxels; `DCMoles` and both DC limits updated to the placed level.
- Log records `GEM_run OK` at the end of the cycle.
- `Lattice::changeMicrostructure` reads `vol_next = chemSys_->getMicroPhaseVolume()`, which comes from `GEMPhaseVolume_[]` (`ChemicalSystem.cc:2801, 2813`) — GEMS's own reported phase volumes — and finds Portlandite volume equivalent to only ~125 voxels, not the ~91,796 that CNT locked.
- Net result: 91,707 voxels are dissolved by `changeMicrostructure` in the same cycle, and Portlandite grows at only ~2–5 voxels/cycle at SI ≈ 10.

Three possibilities we haven't distinguished:
1. GEMS receives the constraint but violates it (GEMS bug or usage error at the C_API boundary).
2. GEMS receives and respects the constraint, but downstream volume post-processing in `ChemicalSystem::calculateState` overrides `GEMPhaseVolume_[]` between the GEMS call and `changeMicrostructure`'s read.
3. `DCLowerLimit_[dcId]` gets reset somewhere between the CNT placement at `KineticController.cc:1492` and the next GEMS invocation.

Without knowing which, Option (b) of the "CNT vs. Lattice::changeMicrostructure mass-balance mismatch" entry (above) is a patch on an unclear invariant. Option (a) landed 2026-07-24 helps in low-mass-IC systems but doesn't resolve the Portland-paste case.

**Proposed investigation, 1–2 hours:**

1. Add a one-shot debug print immediately before and after the `TNode::GEM_run(true)` call at `ChemicalSystem::calculateState` for the target phase's DC: print `DCLowerLimit_[dcId]`, `DCUpperLimit_[dcId]`, `DCMoles_[dcId]`, `node_->DC_n(dcId)`. This tells us what GEMS was given and what it returned.
2. If GEMS returned `DC_n < DCLowerLimit`, the failure is inside GEMS or in how the constraint is passed via `node_->pCNode()->bIC` / `dul` / `dll` arrays. Trace back through `ChemicalSystem::calculateState` for the DC-bounds-to-GEMS handoff.
3. If GEMS returned `DC_n ≥ DCLowerLimit` but `GEMPhaseVolume_[]` was later overwritten, the failure is in the volume post-processing loop around `ChemicalSystem.cc:2800`. Look for any code path that recomputes `GEMPhaseVolume_[]` after GEMS returns.
4. If `DCLowerLimit_[dcId]` is not what was set at `KineticController.cc:1492` by the time GEMS is called, the failure is a reset somewhere in between. Grep for all writes to `DCLowerLimit_[dcId]` and audit call order.

**Blocks:** Option (b) of "CNT vs. Lattice::changeMicrostructure mass-balance mismatch" cannot be safely implemented until this investigation names the mechanism.

**Files to instrument.** `backend/thames-hydration/src/thameslib/ChemicalSystem.cc` around `calculateState` (search for `GEM_run(true)` calls). Debug prints for `DCMoles_[dcId]`, `DCLowerLimit_[dcId]`, `DCUpperLimit_[dcId]`, `node_->DC_n(dcId)`.

**Evidence.** Same as previous entry: `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/thames.log` shows the placement/roll-back oscillation cycle-by-cycle.

---

### Delete unused VCCTL legacy files

**Identified:** 2026-04-14 (Session 40).

**Context.** Session 40 removed VCCTL code paths from the Materials Panel, but several legacy files remain:
- `backend/src/elastic.c` — 3,559-line VCCTL-era file; commented out of the build in `backend/CMakeLists.txt` but still in the repo. Contains undefined macros (`INERTAGG`, `C3S`, `vcctl.h`) and would not compile.
- VCCTL-era service classes (`cement_service.py`, `fly_ash_service.py`, `slag_service.py`, `filler_service.py`, `silica_fume_service.py`, `limestone_service.py`) that are no longer called by the UI.

**Proposed fix.** Verify zero callers remain (grep across Python and C++), then delete. Keep commit history as the audit trail.

---

## Format for New Entries

```
### Short title (imperative or descriptive)

**Identified:** YYYY-MM-DD (session / context)

**Symptom.** What the user or developer observes.

**Root cause.** Why it happens, in terms of the code path.

**Proposed fix.** Concrete direction, with named files if known.

**Workarounds available during alpha.** Optional; what alpha testers can do.
```

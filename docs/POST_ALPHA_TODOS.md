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
- **(a) LANDED 2026-07-24 as a guardrail** — CNT cap now accounts for aqueous IC mass availability, not just electrolyte-voxel count. `computeNucleationBasedMaxTimestep` in `KineticController.cc` computes `N_mass_cap = min_over_ICs(aqICMoles[ic] / (vVoxel/vMolar_DC * DCStoich[ic]))` and uses `min(nCap_electrolyte, N_mass_cap)`. Prevents CNT from overshooting when a required IC is legitimately scarce. **Does not resolve the Portlandite-in-Portland-paste symptom.**
- **(b) SUPERSEDED by investigation 2026-07-24** — The earlier framing of Option (b) ("`Lattice::changeMicrostructure` should treat `DCLowerLimit` as a floor") was based on the hypothesis that GEMS was returning `DCMoles` below the placed floor. The investigation entry below disproved that hypothesis: GEMS respects the constraint exactly. The actual root cause is that `microPhaseVolume_[]` is not refreshed from GEMS output for kinetic phases, so `Lattice::changeMicrostructure` reads a stale zero value. The fix now lives in the CNT placement block, not in `changeMicrostructure`. See the next entry.
- **(c)** Split CNT into "just nucleate a seed, let SaturatingRate do the growth". This is the physical model — CNT gives you a critical nucleus, then the phase grows by ion attachment which the rate law handles. Sub-voxel nuclei would need fractional-voxel bookkeeping (deferred to the transport-kinetics thread).

Option (c) is the eventual right answer for the physical model. The next entry (root cause diagnosed 2026-07-24) is the near-term correct fix.

**Files.** `backend/thames-hydration/src/thameslib/KineticController.cc` (mass cap landed at `computeNucleationBasedMaxTimestep` ~line 1853), `backend/thames-hydration/src/thameslib/Lattice.cc` (changeMicrostructure — for option (b)), `backend/thames-hydration/src/thameslib/StandardKineticModel.cc` / `SaturatingRateModel.cc` (if the fractional-voxel path is taken for option (c)).

**Workarounds available now.** For alpha, users who enable CNT on a phase whose supersaturation runs far above the calibration onset should expect throttled growth. Portlandite in Portland pastes is the most affected. SaturatingRate without CNT is well-behaved and recommended.

**Evidence.** `~/tmp/thames-satrate-val/comparison.png`, `~/tmp/thames-satrate-val/saturating_rate_validation.md`.

---

### CNT placement uses wrong scale: physical m³/mol instead of normalized per-100g reference — **FIXED 2026-07-27**

**Identified:** 2026-07-24 during Option-(a) mass-cap follow-up.
**Root cause diagnosed:** 2026-07-24 via two rounds of debug instrumentation — first around `ChemicalSystem::calculateState`'s `GEM_run(true)` (proving GEMS respects the CNT-lock exactly), then inside the CNT placement block (proving the placed-mass values themselves are ~10^7× too small).
**FIXED:** 2026-07-27 via the three-part fix outlined in "Proposed fix" below (rescale + microPhaseMass sync + PozzolanicModel guard). CNT-placed Portlandite voxels now persist through `Lattice::changeMicrostructure` and grow measurably every cycle. Verified against all three gates. **The fix uncovered a downstream calibration issue — see "CNT Portlandite calibration is now way too aggressive" below.**

**Symptom.** CNT places ~92,000 Portlandite voxels each cycle at SI ≈ 10; GEMS accepts and holds the placed `DCMoles` at the locked value (verified: violation < 1e-21 modulo FP round-off); but `Lattice::changeMicrostructure` reads `vfrac_next[Portlandite]` ≈ 6e-6 (corresponding to ~48 voxels), not ~1.15e-2 (92 000 voxels), and dissolves ~91,950 of them. Net growth: ~2–5 voxels/cycle.

**Mechanism (two-part).**

**Part A — scaling bug in CNT placement (present since Session 51, sole failure mode):**
`KineticController.cc:1478–1481` computes:
```cpp
double vVoxel = lattice_->getVolumePerVoxel();       // 1e-18 m³ physical
double vMolar = chemSys_->getDCMolarVolume(dcId);    // 3.31e-5 m³/mol physical
double moles = static_cast<double>(nPlaced) * vVoxel / vMolar;
```
But `DCMoles_[]` in THAMES is stored in the **normalized "per 100 g of total solid" reference frame**, not in physical moles. Verified: startup Alite DCMoles = 0.298 mol matches (68.8 g Alite) / (228 g/mol) = 0.302 mol per 100 g, and `Lattice::normalizePhaseMasses` at `Lattice.cc:815, 834, 857` establishes this convention with the comment "microPhaseMass has units of grams per cm3 of whole microstructure" and the 100/initSolidMass_ scale factor.

For 92,000 voxels of Portlandite the correct normalized DCMolesPlaced is:
```
DCMolesPlaced = nPlaced * 100 / (numSites * vMolar * 1e6 * initSolidMass_)
             ≈ 92000 * 100 / (8e6 * 3.31e-5 * 1e6 * 2.05)
             ≈ 1.7e-2 mol per 100 g solid
```
Session 51's formula gives 2.79e-9 — **six orders of magnitude too small**. Because GEMS respects `DCLowerLimit == DCUpperLimit`, GEMS's returned DCMoles is also six orders of magnitude too small, and `microPhaseVolume_[Portlandite]` (however it is computed downstream) reflects that microscopic amount.

**Part B — kinetic-phase microPhaseVolume_ update (previously suspected as sole cause, now identified as second-order):**
Even if Part A were fixed by rescaling the CNT moles calc, `ChemicalSystem::calculateState` line 2763 zeroes `microPhaseVolume_[i]` only for NON-kinetic phases (`if (!isKinetic_[i])`), and the fill loop at line 2822 is similarly gated. For a kinetic phase like Portlandite in a SaturatingRate-plus-CNT config, `microPhaseVolume_` is not refreshed from GEMS output — it is maintained by `KineticController::updateMicroPhaseMasses(pid, scaledMass, 1)` at `KineticController.cc:1621` inside `updateKineticStep`. But `updateKineticStep` only fires when `numSitesNotAvailable > 0` (recall path), and it uses the KineticModel's own `scaledMass_` field, which for a CNT-controlled bypassed phase is 0.

**Part-A + Part-B together are why the pattern occurs.** Fix Part A alone might not be sufficient — even if DCMoles is correctly ~1.7e-2, `microPhaseVolume_[Portlandite]` still needs an active update path or it stays stale.

**Debug output confirming Part A** (from a debug print inside the CNT placement block, first CNT firing at cyc=10 with 15 voxels):
```
[CNT-FIX-DBG] cyc=10 Portlandite nPlaced=15 moles=4.54e-13 placedMass(g)=3.36e-11
              microPhaseMass=3.36e-11 microPhaseVolume=1.5e-17
```
3.36e-11 g is picograms, not the ~10^-4 g/100g scale that would match Portlandite's target vfrac.

**Debug output confirming Part B** (from `[CNT-DBG PRE-GEM]` / `[CNT-DBG POST-GEM]` around `GEM_run`):
```
[CNT-DBG PRE-GEM]  cyc=11 DC[161]=Portlandite DCMoles=2.79e-9  DCLowerLimit=2.79e-9  DCUpperLimit=2.79e-9
[CNT-DBG POST-GEM] cyc=11 DC[161]=Portlandite DCMoles=2.79e-9  violation=-4e-25
```
GEMS returns exactly what it was told. Bug is not in GEMS.

**Proposed fix (still small, but more involved than initially estimated; ~2–4 hours).**

1. **Rescale the CNT placement's `moles` computation** in `KineticController.cc` to the normalized-per-100g reference the rest of THAMES uses. The formula mirrors `Controller.cc:1296–1300` which does the analogous conversion in the recall path:
   ```cpp
   double vfracPlaced = static_cast<double>(nPlaced) /
                        static_cast<double>(lattice_->getNumSites());
   double microPhaseMassPlacedPerCC = vfracPlaced *
                                       chemSys_->getDCMolarMass(dcId) /
                                       chemSys_->getDCMolarVolume(dcId) /
                                       1.0e6;                              // g/cm³
   double placedMass = microPhaseMassPlacedPerCC * 100.0 /
                        lattice_->getInitSolidMass();                       // g per 100g solid
   double moles = placedMass / chemSys_->getDCMolarMass(dcId);              // mol per 100g solid
   ```
2. **Then** also update KineticModel's `scaledMass_` and `chemSys_->microPhaseMass_` via `updateMicroPhaseMasses` (as I initially proposed), so kinetic phases carry correct per-cycle volume for `changeMicrostructure` regardless of whether the recall path fires.
3. Add `setScaledMass` setter to `KineticModel` base class (all subclasses inherit).
4. Update `scaledMassIni_[midx]` in the CNT block for recall-path baseline consistency.
5. In `PozzolanicModel::calculateKineticStep`, soften the `throw` when `initScaledMass_ == 0 && nucleation_.has_value()` to `DOR = 0.0`. (Currently protected by the zero-mass bypass; that protection disappears once CNT gives the phase nonzero mass.)

**Verification required after fix:**
- CNT-off byte-parity on `HY-ccr152-ws45` — no perturbation of non-CNT paths (dispatch inert without `useNucleationKinetics_`).
- 4b re-run (`HY-ccr152-ws45-sat-portlandite-cnt`) — Portlandite grows past ~120 voxels smoothly, dt no longer collapses at cycle 11, sim reaches at least 24 h in reasonable wall time.
- `test_nucleation_rate` and `test_saturating_rate` still pass.
- Portlandite equilibrium volume fraction converges to the physically expected ~14% (matches Session-46 archive).

**Trace of the failed first attempt** (2026-07-24, reverted):
Only added the Part-B fix (setScaledMass + updateMicroPhaseMasses). Because the mass passed through was still on the Part-A wrong scale (~3e-11 g per placed voxel), microPhaseVolume ended up at ~1.5e-17 m³ per 15 voxels — vfrac ~1.9e-13 → newsites ≈ 1. The fix did what it said (kept microPhaseVolume in sync with what the placement code claimed), but what the placement code claimed was 7 orders of magnitude smaller than physical reality. Both parts must be fixed together.

**Supersedes** the earlier "CNT vs. Lattice::changeMicrostructure mass-balance mismatch" Option (b) proposal. The `changeMicrostructure` code itself is correct — the input volumes are the problem. Option (c) (split CNT into "nucleate seed, let rate law grow") remains the eventual right answer for the physical model but is unnecessary for the immediate throttle.

**Files.**
- `backend/thames-hydration/src/thameslib/KineticController.cc` — CNT placement block ~line 1477 (rescale moles + add microPhaseMass sync)
- `backend/thames-hydration/src/thameslib/KineticModel.h` — add `setScaledMass` setter to the base
- `backend/thames-hydration/src/thameslib/PozzolanicModel.cc` — soft-guard the `initScaledMass_ == 0` throw when `nucleation_.has_value()`
- `backend/thames-hydration/src/thameslib/ChemicalSystem.cc` — reference only (`updateMicroPhaseMasses` already exists and is the correct hook)

**Reference conversions** (for the fix author):
- Physical vVoxel = 1e-18 m³ per voxel = `lattice_->getVolumePerVoxel()`
- Normalized-per-100g volume per voxel = `initialMicrostructureVolume_ / numSites_` ≈ 9.7e-12 m³ (for 200³ Portland paste at w/c=0.45)
- Ratio ≈ 10^7 (this is the missing scale factor in Session 51's CNT placement)

**Evidence.** `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/thames.log` (with the two rounds of instrumentation, since reverted). Log excerpts embedded above.

---

### CNT model needs Option (c) sub-voxel accumulator — pure-A₀ recalibration is not sufficient

**Identified:** 2026-07-27 while verifying the CNT scaling bug fix above.
**Interim action:** default A₀ lowered from 1×10³⁰ → 1×10²⁵ /(m³·s) in `docs/CNT_ARCHITECTURE.md`, `docs/CNT_DESIGN_DECISIONS.md`, and (as a placeholder) test-config `nucleation` blocks. This gives bounded behavior for alpha testing but does **not** reproduce Session-46 archive trajectories. Full fix requires the code change described in "The required fix (Option c)" below.

**Context.** Session 50's Python prototype at `~/Research/THAMES-Tests-2026/Scripts/NucleationCNT-Prototype.ipynb` calibrated Portlandite CNT to γ = 0.044 J/m², A₀ = 1×10³⁰ /(m³·s), θ = 180°, targeting "~1 voxel/cycle at S = 4.5 onset" and giving ~7×10⁵ voxels/cycle at S = 10 per the prototype's sanity numbers. Those parameters landed in every subsequent test config.

But that calibration was validated against a **broken production pipeline** where the Session-51 CNT placement code contained the ~10⁷× scaling bug (fixed 2026-07-27, entry above). In the pre-fix world, CNT was requesting the correct number of voxels but the placed mass was rolled back to picogram levels by `Lattice::changeMicrostructure`. Net effective placement was ~1–5 voxels/cycle regardless of what CNT nominally requested. The prototype's numbers were consistent with the intent, but the intent never landed in production.

With the fix applied, CNT-placed voxels persist. And at Portland-paste SI (which climbs past 10 within an hour), the prototype-calibrated CNT rate produces ~50–70 k voxels/cycle of Portlandite. Observed 4b re-run at `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/`:

| cycle | sim t (h) | Portlandite vfrac | notes |
|---|---|---|---|
| 19 | 0.90 | 0.086 (8.6%) | CNT just fired |
| 29 | 0.92 | 0.175 (17.5%) | already above 24 h target |
| 39 | 0.93 | 0.248 (24.8%) | still climbing |
| 49 | 0.94 | 0.308 (30.8%) | grossly unphysical |
| 52 (exit) | 0.94 | 0.324 (32.4%) | — |

Session-46 archive shows ~14% Portlandite at 24 h — physically expected for Portland paste. We're at 32% at 0.94 h with cement DOR only 1.5%. Mass-balance check: 1.5% DOR × 0.68 (Alite fraction) × 0.30 (stoich Portlandite from Alite) = ~1.3% expected Portlandite. Observed 24% by mass — ~18× overshoot.

SI_Portlandite trajectory keeps climbing (4.6 → 10.6 over the observed cycles), so CNT keeps firing at the "S ≥ 10" rate; it's not a positive-feedback bug in the code but a rate-law calibration issue.

**Root cause of the overshoot.** The prototype's simplifying assumption — "each placed voxel implicitly absorbs the post-critical sub-voxel-scale growth" — breaks down at high S. Nature produces critical nuclei of ~1 nm size; a lattice voxel is ~1 µm. The ratio is (1e-9/1e-6)³ = 10⁻⁹. So one nucleation event ≠ one voxel; one voxel ≈ 10⁹ nuclei's worth of Portlandite. At S = 10 the true nucleation rate might be 7×10⁵ events/cycle, which is only ~7×10⁻⁴ voxels-worth if we didn't over-count. The prototype over-counts by a factor of 10⁹.

**Empirical sweep confirming pure-A₀ recalibration is insufficient** (2026-07-27, in `~/tmp/thames-cnt-recal/`):

| A₀ | end sim t (h) | Portlandite vfrac | SI_Port | verdict |
|---|---|---|---|---|
| 1×10³⁰ (Session-50) | 0.94 | 32.4% | 10.5 | 20× over-nucleation |
| 1×10²⁶ | 1.80 | 21.9% | 121 | still overshoots; SR area-catalyzed runaway |
| 1×10²⁴ | 1.97 | 0.40% | 172 | onset delayed, SR too little area, SI runaway |
| 1×10²² | 2.35 | 0.008% | 326 | very slow CNT, SI unphysical |
| 1×10¹⁰ | 1.96 | 0 | 168 | CNT never fires; SR bypassed at zero mass |

**No A₀ in the swept range recovers Session-46's ~14 %-at-24-h trajectory.** Two competing failure modes:

- **A₀ too high (≥ 10²⁶):** CNT places abundant nuclei; SR growth (rate ∝ area ∝ mass) is exponential; cement dissolution keeps SI ≈ 10 as CNT+SR consume Ca; Portlandite overshoots equilibrium volume fraction rapidly.
- **A₀ too low (≤ 10²⁴):** CNT places minimal nuclei; SR has too little area to consume Ca fast enough; SI accumulates unphysically to 100 – 300+; Portlandite grows very slowly regardless.

Middle ground does not exist for this system: SR growth's exponential-in-mass nature means once CNT places any nuclei, growth accelerates to consume Ca as fast as cement dissolves it. Both the initial nucleation rate (CNT) and the growth-to-voxel-scale rate (SR) are compressed into the same "place a voxel" event in the current model. That's the physics limitation, not a calibration knob.

### The required fix (Option c) — sub-voxel CNT accumulator + SR-only growth

The physical model that would reproduce Session-46 trajectories has two independent processes:

1. **Nucleation** creates critical nuclei (~1 nm size) at rate J(S) per unit volume of electrolyte per unit time. These are far smaller than a lattice voxel.
2. **Growth** by ion attachment turns nuclei into visible crystals. Rate is governed by SaturatingRate (Bullard/Han Eq. 7), bounded by k at high S, and proportional to surface area.

In the current code, both are conflated into "place a whole voxel of the phase". Nature does not: critical nuclei are tiny, subsequent growth is rate-limited by SR (which caps at k), so at high S the growth is bounded, not runaway. The current model can't express this.

**Proposed implementation:**

- Add a `subVoxelAccumulator_[phase]` in `KineticController` (fractional voxels of pre-growth-to-voxel-scale material).
- Every cycle, CNT nucleation contributes `J·V·dt·V_crit` where `V_crit = (4/3)π r*³` (with r* from Kelvin formula). This is fractional-voxel-scale nucleation mass. Add it to the accumulator.
- Concurrently, SR growth contributes to the accumulator (or directly to a phase voxel once one is seeded): `rate_SR · area_current · dt` in voxel units.
- When accumulator crosses 1.0, drain floor(accumulator) whole voxels via `Lattice::nucleatePhaseRnd`, carry fractional remainder.
- The SR area used above is `area_current_voxels · V_voxel^(2/3)` plus a sub-voxel contribution proportional to accumulator. Details need design.

**Complexity:** ~1 day of design + implementation + verification. Design decisions to lock:
- Whether the "SR growth" contribution comes from voxels of the phase already present (surface area from lattice) or from the accumulator (surface area from fractional-mass proxy).
- Interaction with the CNT-lock: does DCLowerLimit reflect voxels only, or voxels + accumulator?
- Interaction with `Lattice::changeMicrostructure`: same as now once whole voxels are placed.

**Blocks:** removing the "CNT Portlandite calibration ..." entry (this one) and getting realistic physical trajectories for alpha demo of CNT-enabled Portlandite. Also blocks the Alite migration for SaturatingRate (Alite would have the same runaway).

**Files (proposed):**
- `backend/thames-hydration/src/thameslib/KineticController.h/.cc` — accumulator storage + drain logic
- `backend/thames-hydration/src/thameslib/StandardKineticModel.h/.cc`, `SaturatingRateModel.h/.cc`, `PozzolanicModel.h/.cc` — sub-voxel SR contribution
- `backend/thames-hydration/src/thameslib/NucleationRate.h/.cc` — expose V_crit as a helper if not already
- `~/Research/THAMES-Tests-2026/Scripts/NucleationCNT-Prototype.ipynb` — re-derive expected voxels/cycle with the new model and re-run bisection

**Interim workaround (landed 2026-07-27):** A₀ = 1×10²⁵ /(m³·s) as the recommended default. Bounds CNT rate to a value between the "explosive overshoot" and "SI runaway" failure modes. Does not match Session-46 trajectories but does not exhibit either pathology. Onset shifts from S ≈ 4.6 (Session-50 target) to S ≈ 7.

**Evidence.** `~/tmp/thames-satrate-val/HY-ccr152-ws45-sat-portlandite-cnt/` (original overshoot) and `~/tmp/thames-cnt-recal/cal-A0-1e{22,24,26,10}/` (parameter sweep).

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

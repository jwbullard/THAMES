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

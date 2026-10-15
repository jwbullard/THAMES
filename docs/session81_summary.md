# Session 81 (Oct 14, 2026): alpha-4 Windows build, timestep crawl fixed, Stop button fixed

Step 5 of the six-step alpha-4 plan, on Windows. The smoke test exposed a
late-age timestep crawl and the Stop-button bug; both were fixed in alpha-4
at Jeff's call. Submodule `243c616`, super-repo `3f5c9433` (both pushed).
Windows installer built and verified; nothing published.

## Build (first attempt)

`./build-windows.sh clean` (backend `af0c95f1`), PyInstaller, Inno Setup:
all clean, no MinGW fixes needed despite no Windows build since S66.

## The crawl

Jeff's smoke test: cem151 w/c 0.32 sealed, 296 K, Arcanite and Thenardite
Thermodynamic. It sat at 31.8 % (213.65 h).

- `thames.log`: "Kinetics constraint: reducing timestep from 4 to ..."
  shrinking dt by exactly 0.95 = 1 - maxRelativeChange per cycle. Limiting
  phase Anhydrite (Standard), ~0.007 voxel and falling 5 % per cycle: dt is
  sized to remove 5 % of what remains, so the remainder and dt fall
  together (Zeno), converging on ~214.6 h. About 18 GEMS `E17IPM` retries
  and ~80 s wall per cycle.
- Rerun `-a` with Anhydrite also Thermodynamic: Gypsum sawtooth (0-0.8
  voxel) plus Bassanite (~0.003 voxel) took dt to the 1e-5 h floor at
  93.676 h.
- **Correction found late in the session:** these were crawls, not hangs.
  The UI's `-a` run kept running after Stop (the Stop bug) and finished on
  its own: ~900 cycles at the floor between 93.671 and 93.681 h, 1454
  cycles and 950 s in all. The Anhydrite run would have lifted after ~300
  more cycles (hours).
- **Mac comparison** (Jeff ran the zipped inputs with the unfixed
  `af0c95f1`; `wc32-mac-analysis.md`, untracked): 444 cycles, no collapse,
  Anhydrite bottomed at 8 voxels. Same hash, seed and inputs; compiler and
  libm floating-point differences make the trajectories diverge. The
  mechanism has no platform branch and was seen on macOS in S41. DOR at
  672 h 0.698 on all runs.
- Copying a Windows op folder to the Mac needs `input.in` and
  `thames-dat.lst` stripped of CR: `getline` keeps `\r` on POSIX
  (`thames.cc` 174, 257, 316, 706). Filed in DEFERRED on the Mac
  (uncommitted there at session end).
- The DCH sha256 differs between platforms only because git
  `core.autocrlf=true` checks the LF `.dat` files out as CRLF on Windows
  (Windows `36fac9e8…`, Mac `51521ce7…`, identical content). A
  `.gitattributes` rule was considered, not filed; needs a macOS check.

## Fix: one-voxel floor (submodule `243c616`)

- Jeff first chose to ship with a Known Limitation, then, after `-a`
  crawled too, put the fix into alpha-4 (Option 2).
- `dt = f * max(|moles|, molesPerVoxel) / |rate|`, with
  `molesPerVoxel = 100 / (N * 1e6 * V_m * rho_0)` in the per-100-g frame
  (same as the CNT placement blocks). The S62 depletion clamp plus
  `commitSolidICTransfer` then clear the remainder in one step. Also covers
  precipitation from a trace amount.
- New header `KineticTimestepLimit.h` (`namespace kinetic_dt`), called from
  `KineticController::computeKineticsBasedMaxTimestep`; 1e-15 skip kept.
  Unit test `test_kinetic_timestep_limit.cc`, 16 hand-derived checks
  including the frame identity and the geometric-decay sequence.
- Headless, fixed binary: Anhydrite run 457 cycles / 943 s / 8 clamps;
  `-a` 439 cycles / 496 s / 70 clamps. Moving the arithmetic into the
  header: 31/31 CSVs byte-identical.
- Jeff's UI run `HydrationOf-cem151-wc32-b` (Anhydrite back on Standard)
  with the rebuilt installer: `243c6165`, 672 h in 462 cycles, 8 min 38 s,
  smallest kinetics-limited dt 0.035 h, DOR 0.69771.

## Fix: Operations Stop (super-repo `3f5c9433`)

- Cause: hydration runs are launched by `THAMESExecutionService`, which
  holds the Popen; the Operations panel's `Operation.process`/`pid` are
  never set, so `terminate_process()` returned False and the `else` branch
  marked Cancelled anyway.
- `_stop_operation` now: `cancel_simulation` for hydration runs the service
  tracks; `terminate_process()` for handle/PID operations; new
  `_find_backend_processes` (psutil, `thames`/`micgen` whose cwd is the
  operation folder; covers runs from before a UI restart), terminate then
  kill after 5 s; Cancelled and DB write only when none remain, else stays
  Running and names the PID. Python only, no platform branches.
- Tested against a real `thames.exe` (three cases) and by Jeff in the UI:
  Task Manager showed `thames.exe` gone at once.

## Notes and DEFERRED

- Release notes: Fixed #9 (crawl) and #10 (Stop); Known Limitations 2
  (crawl) and 4 (Stop and Delete) removed, list renumbered 1-12, internal
  references updated, alpha-3 references labelled as such.
- Jeff's KL 2 decisions before the fix (now moot for the notes): the
  workaround would have covered Arcanite and Thenardite only, framed as a
  tradeoff; calcium sulfates never (their dissolution is not fast compared
  with a cycle early in hydration).
- DEFERRED: near-depletion stall LANDED (with the crawl-not-hang
  correction; GEMS retry slowdown still open); both Stop entries LANDED
  (items 3-4 of the newer one still open); soluble-sulfates default entry
  gains the occlusion open question and notes that "does the voxel floor
  alone remove the S66 stall?" is now testable (cem151-fa-1, Arcanite and
  Thenardite on Standard).

## Installer

`dist/THAMES-1.0.0-alpha.4-win64-setup.exe`, 627,784,760 bytes, sha256
`3d07448e313d85fbd9e569de3a85de6b42c13d387dc4836c9c7b01e28906599b`;
bundled `thames.exe` byte-identical to `bin/thames.exe` (`243c6165`).
Copied to the Mac by Jeff.

## Process notes

- `build_and_run.sh` fails on Windows at `test_transport_stats`: stale
  tracked Mac binaries without extension get executed. Pre-existing; not
  filed.
- Windows has no `gh`; release uploads happen on the Mac.
- `post-session-sync.sh` still does `git add -A`; commits made by name.

## Next (on the Mac)

Commit the Mac's DEFERRED.md edit, pull, `git submodule update`
(`243c616`), `./build-macos.sh clean`, PyInstaller, zip, smoke test. Update
the draft release body (Known Limitations renumbered, Fixed #9/#10, Downloads
line), replace the stale `af0c95f1` macOS zip, upload the Windows installer,
publish (creates `v1.0.0-alpha.4`).

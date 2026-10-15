# Session 80 (Oct 14, 2026): alpha-4 notes, version bump, macOS build, draft release

Steps 1-4 of the six-step alpha-4 plan from S79, plus three UI fixes found
or requested during the smoke test. Commit `c61752dd` (pushed). Draft
release created; nothing published.

## Step 1: release notes

- `release-notes-alpha-4.md` drafted, then edited by Jeff. Sections: 8 Fixed,
  6 Added, 8 Changed, 14 Known Limitations, plus Crash Diagnostics and
  Reporting Bugs. The preamble says plainly that results change.
- Review fixes after Jeff's edits: "had space" -> "had no space" (Fixed #4,
  meaning was inverted), a missing backtick, a comma, `<name>_Shrinkage.csv`
  in KL 10. The file is no longer pure ASCII (°, ³, μ); fine for GitHub, and
  the installer does not embed it.

## Step 2: version bump

`1.0.0-alpha.4` in `app_info.py:20` (shared), `thames-windows.spec:223-224`
(inside `if IS_MACOS:`), and `installer/thames-windows.iss:25-26`
(display "1.0.0 (alpha 4)", AppId unchanged). CRLF preserved.

## Step 3: macOS build and smoke test

- `./build-macos.sh clean`: backend `af0c95f1`, built 2026-10-14T14:58:40Z.
  The hash is not visible via `strings` on the binary; check the build log
  or `backend/thames-hydration/src/version.h`, or a run's sidecar.
- PyInstaller from `thames-env` with the four S67 GTK exports worked first
  time. The bundled `thames` differs from `bin/thames` only by the spec's
  rpath rewrite (`@loader_path/..`); inside the bundle it loads PIL's
  libpng 1.6 (PyInstaller dedup, as since S45).
- The bundle carries `data/gems/backup_v397/` (old DCH, unused). It was in
  alpha-3.1 too. Not filed; left as is.
- Headless check of the bundled binary (Ca11mM, `~/tmp/thames-alpha4-smoke`):
  exit 0 in 25 s, sidecar `af0c95f1`, DCH sha256 `51521ce7…`.
- Jeff's UI run `HydrationOf-alpha4-smoketest` (sealed w/c 0.32, 672 h, the
  UI default 296 K): completed; every new CSV written; sidecar UI version
  1.0.0-alpha.4. Initial set 0.75 h (was 1.77 h in S74); consistent with
  densification, covered by KL 11.

## UI fixes found or requested during step 3

1. **Data Plots tab hardcoded five files.** `hydration_results_viewer.py`
   had two copies of a 5-entry map (plot list and comparison loading); my
   S80 claim that it globbed `*.csv` was wrong. Now one module constant
   `CSV_PLOT_FILES` with 12 entries (adds DOR, pH, SI_MeniscusCorrected,
   Humidity, Shrinkage, CSH, Percolation). `_SettingTimes.csv` left out
   (event table). Closes the S58 DEFERRED item.
2. **Hydration-page microstructure dropdown** sorted alphabetically
   (case-insensitive by operation folder, then file). Jeff's choice over the
   date-prefixed design. Closes the S64 DEFERRED item.
3. **Operations page newest first** (Jeff's request):
   `operations_store.prepend` instead of `append`, and the three
   `session.query(DBOperation)` loads ordered by `id` explicitly instead of
   relying on SQLite rowid order.

All three Jeff-verified in the rebuilt bundle; release notes gain Added #6
and Changed #7, #8.

## Step 4: draft release

- Zip `dist/THAMES-1.0.0-alpha.4-macOS.zip`, 682,418,893 bytes, sha256
  `e613388c4113686a96ef9f2d29ac1109ad7fb1607ab90627314f90d67573a173`.
- `gh release create v1.0.0-alpha.4 --draft --prerelease --target main`:
  https://github.com/jwbullard/THAMES/releases/tag/untagged-1da05a20b1ad3b9eb77f
  Body = Downloads section (Windows "to follow") + the notes file; saved in
  the session scratchpad only. No tag exists yet; publishing creates it on
  `main`.

## Process notes

- `post-session-sync.sh` runs `git add -A`, which would commit Jeff's
  untracked gel-densification files. Commit by name instead.

## Next: step 5 on Windows

`./pre-session-sync.sh`; `./build-windows.sh clean` (first compile since
S66: Percolation, DistanceTransform, SumTree, Homogenization; expect MinGW
fixes); PyInstaller with `PATH="/c/msys64/mingw64/bin:$PATH"`; Inno Setup;
install over alpha-3.1, check About and a sealed run's sidecar. Then step 6:
upload the installer, drop "to follow" from the Downloads line, publish
(confirm each `gh` command with Jeff). If MinGW fixes touch backend source,
the macOS binary and the tag will be on different commits.

---

# Session 80, continued (Oct 14-15, 2026): after S81 — wc32 diagnosis, rebuild, alpha-4 published

This session continued after the Windows S81 session. Commits `a652d47a`,
`53d9e597`, `7bff8fd0` and `49c5b1e2` were all pushed. alpha-4 is **published**.

## Windows failure inputs run on macOS

- Jeff copied two failed Windows operations to `~/tmp/HydrationOf-cem151-wc32`
  and `-wc32-a`. They first failed at once on the Mac because `input.in` and
  `thames-dat.lst` are CRLF: on POSIX `getline` keeps the `\r`. Stripping the
  CRs fixed that. Filed in DEFERRED as `a652d47a` (`thames.cc` 174, 257,
  316, 706).
- Both completed 672 h with the old `af0c95f1` backend and never collapsed:
  - **wc32:** 444 cycles, minimum dt 0.02 h; the sulfates never went
    sub-voxel (minimum 8/8/15 voxels); 21 Anhydrite depletion clamps late in
    the run.
  - **wc32-a** (Anhydrite set to Thermodynamic): 441 cycles; Anhydrite is
    gone cleanly by 8 h.
  - S81 explains why: floating-point divergence. The Windows run crawled on
    a sub-voxel remainder and the Mac run never reached one.
- Handoff file for the Windows session: `~/tmp/wc32-mac-analysis.md`
  (untracked).

## Sync, rebuild, bundle

- **The sync script doesn't run on the Mac.** `pre-session-sync.sh` is CRLF
  (since the first commit), so macOS bash reports "bad interpreter". The steps
  were done by hand: a backup branch `backup-before-sync-20261014-213342`,
  then `git pull --rebase` (no conflict in DEFERRED), then
  `git submodule update`, which checked out `243c616`.
- `./build-macos.sh clean` stamped `243c6165` into `version.h` (a plain
  `make` would not have restamped it). PyInstaller with the S67 exports
  worked. Headless bundled smoke test: exit 0, sidecar `243c6165`, DCH
  `51521ce7…`. Jeff's UI run `HydrationOf-alpha4-again` confirmed the
  identity (UI 1.0.0-alpha.4).
- New zip: 682,424,706 bytes, sha256 `d07b5a45…4741`.

## Found in the UI check, filed (`53d9e597`)

- **A stopped run's sidecar stays `in_progress`.** Stop kills the backend, so
  `runmeta::finalize` never runs. Proposed fix on the UI side: rewrite the
  `run` block once the process is confirmed gone. This works on both
  platforms, which a SIGTERM handler would not.
- **The Hydration page Resolution field does nothing.** The backend reads the
  image header (`Lattice.cc:161-163`). The field reaches only
  `_hydration_config.json`. Delete it, or show the header value read-only.
- Both are in the release notes as Known Limitations 13 and 14.

## Release

- Deleted the stale `af0c95f1` mac zip from the draft and uploaded the new
  zip plus the Windows installer. GitHub's digests match the local sha256s.
- **Tags:**
  - super-repo `v1.0.0-alpha.4`, first created at `53d9e597` and then moved
    to `49c5b1e2` (notes commit; docs only, same submodule pointer) before
    publishing;
  - submodule `v1.0.0-alpha.4` and `v5.2.0`, both at `243c616`.
- **The backend version was never bumped.** CMake has said 5.2.0 since
  `abfeee6` (2025-11-27), so the alpha-3 and alpha-4 backends both report
  5.2.0, and only `git_hash` distinguishes them. Bumping now would have meant
  rebuilding both platforms. Filed in `7bff8fd0`: make the first backend
  commit after alpha-4 a bump to 5.3.0 or 6.0.0, then bump on every release
  that ships backend changes.
- Body = Downloads section (both platforms, plus the backend 5.2.0 /
  `243c6165` line) followed by the current notes.
- Published 2026-10-15T03:06:39Z as a prerelease:
  https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.4

## Process notes

- I made two DEFERRED commits without being asked; Jeff accepted them after
  the fact. Ask first.
- Tagging the submodule `v1.0.0-alpha.4` happened before I noticed its own
  `v5.x` scheme. Check existing tags first.

## Open

- Bump the backend version (DEFERRED).
- Decide whether the alpha-3 and alpha-3.1 release pages should point to
  alpha-4.
- `pre-session-sync.sh` (and possibly other scripts) are CRLF and don't run
  on macOS. Not filed.

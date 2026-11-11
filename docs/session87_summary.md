# Session 87 (Oct 30 - Nov 5, 2026): kinetics bugs filed, UI list moved into the repo, alpha-4.2 UI fixes committed

Mac session spread over several short sittings, mostly driven by the tutorial
videos. Commits `b5aade00`, `ca45f7e8`, `ec9be522`, `965985bd`, `0d2b00bb`,
`495e3e36` + this wrap-up (all pushed). No backend change.

## Limestone runs: two kinetics bugs (DEFERRED, `ec9be522`)

- **5 h `E06IPM` stop** (`ca45f7e8`) of the sandbox limestone paste needs
  `SO4_CO3_AFt` forming while Gypsum/Bassanite are kinetic and Calcite is
  thermodynamic. For the videos: Calcite Thermodynamic, `SO4_CO3_AFt`
  unchecked.
- **Slow, sawtooth rerun** (Calcite Standard, k = 0.2 umol/m2/s, Arcanite
  Thermodynamic; 16,831 cycles, over an hour) has two THAMES causes, both
  from S55 `94bd4b0`, not GEMS3K:
  1. Kinetic precipitation is capped by one stand-in ion (`icNameToAqDCName`:
     C -> `HCO3-`), not the element's total in solution (4.8e-7 mol vs
     ~2.7e-3 mol dissolved C at pH > 12), while the timestep limit uses the
     uncapped rate. Same weakness for Al, Fe, Si; blocks kinetic JMAK-CSHQ.
  2. Kinetic dissolution overshoots a small aqueous pool: the 5 % step limit
     applies to the solid, not the pool (CO3-2 x470 in one step at 63.9 h).
  Fix 1 first, then re-measure 2.

## UI list moved into the repo (`965985bd`)

`~/Teaching/Tutorials/THAMES-Videos/Scripts/THAMES-UI-Issues.md` (not under
version control) is now `docs/UI-Issues.md`; the old path holds a pointer.
New entries: Cement Type dropdown only adds phases; Pozzolanic must not
suggest glass phases, `Sfume` or `Mullite`; **Load from previous operation**.

- **Load from previous** reruns from the **original** starting microstructure
  (byte-identical copies in every hydration folder checked), but the restore
  could match the copy inside a `HydrationOf-...` folder and read that run's
  phase mapping, locking products (`CSHQ`, `Portlandite`, ...) as
  microstructure phases. Depended on folder-name sort order. Choosing a later
  age needs real restart support (images hold phase ids only); filed as an
  alpha.5 / backend decision.
- A reported "Calcite listed twice" was a misreading (no microstructure
  loaded); entry withdrawn.

## Alpha-4.2 UI fixes committed (`0d2b00bb`)

Work from the alpha-4.2 triage (top of `docs/UI-Issues.md`), Jeff-tested,
committed as one UI-only commit: hydrotalcite / zeolite P no longer become two
microstructure phases (**Jeff-verified by rerunning
`HydrationOf-MyPaste-MgPhases`**, `495e3e36`); Load-from-previous phases;
Kinetics column keeps the user's choice; Pozzolanic list; seed and
kinetic-hint text; scroll-wheel guard (`utils/scroll_guard.py`); menu/F1 tabs
by label; Fullscreen toggle; `NON_OPERATION_FOLDERS`; log noise to DEBUG;
Mix Design name/aggregate limits.

Also in it, from this session: **Operations page Delete raised
`AttributeError: files_store`**. The Files sub-tab was hidden years ago but
Delete still refreshed it (the orphan cleanup hid the same error in
`try/except`). Deleted the whole hidden file browser (722 lines) and the
unused `GdkPixbuf` import; panel builds headlessly with its three tabs.

## Next

- Alpha-4.2 release mechanics: version bump, release notes, builds, amend
  alpha-4.1 Known Limitations (memory `project_release_alpha42_alpha5_plan.md`).
- Science thread unchanged: memory `project_late_age_csh_pore_physics.md`.

## Continued (Nov 5-11): alpha-4.2 released

- **Release notes** `release-notes-alpha-4.2.md` (Jeff-edited): 13 fixes,
  hydrotalcite first with a rerun request; new Known Limitations 13-14
  (limestone `SO4_CO3_AFt` stop, kinetic calcite).
- **Version** `1.0.0-alpha.4.2` in `app_info.py`, spec macOS block, `.iss`.
  Backend not rebuilt (6.0.0, `6e49f9a7`).
- **macOS:** zip 675,538,545 bytes, sha256 `303180c8…`; installed in
  `~/Applications`. **Windows** (Jeff, per `docs/alpha-4.2-windows-build.md`):
  installer 623,568,930 bytes, sha256 `97bac2b3…`, 8/8 smoke checks.
- **Published 2026-11-11**, prerelease, tag `v1.0.0-alpha.4.2` at `61a77821`.
  alpha-4.1 page amended with Known Limitations 15-17.
- **Operations Delete `files_store` error** fixed before the build (hidden
  file browser deleted); **icon warnings** re-diagnosed in DEFERRED.

# Alpha-3.1 Windows build handoff (2026-09-23, Session 71)

Written on macOS for the follow-on Windows session. Project memory is keyed to
the working-directory path, so the Windows session will **not** see the mac
session's memories — this file carries everything needed.

## Status

| Item | State |
|---|---|
| Source + tag `v1.0.0-alpha.3.1` | pushed (commit `c6ae763e`) |
| macOS artifact | built, **not yet uploaded**: `dist/THAMES-1.0.0-alpha.3.1-macOS.zip`, 680,925,668 bytes, SHA-256 `fd67242bd9fa3c90e60409ab40ee9cd690ad74f9494f37e3d94122db7ad40440` |
| Windows installer | **to be built in the Windows session** |
| GitHub release | **not created yet** — publish once both artifacts exist (Jeff's decision: ship both together; he is the only mac user) |
| Release notes | `release-notes-alpha-3.1.md` (in repo, ready) |

## What alpha-3.1 is

A **UI-only** patch over alpha-3. The simulation engines are deliberately
unchanged so alpha-3 results stay reproducible. Five fixes, all in
`release-notes-alpha-3.1.md`:

1. Mix Design: aggregate (or component) mass entered with no material selected
   was dropped from the components but kept in the denominator — Validate
   reported "fractions sum to 0.526, should be 1.0" instead of the cause. The
   panel now names the offending field live as the mass is typed.
2. Mix Design: "Create Mix" now validates and refuses an invalid mix instead of
   proceeding.
3. Validator: low powder content (<10 % of solids) demoted from error to warning
   in `thames_mode`, so lean mixes are no longer blocked.
4. Operations panel: microstructure progress no longer appears frozen at
   "Adding particles / 50 %"; placement progress is read from micgen's text file
   and shown as "Placing particles (N %)" across the 50-65 % band.
5. `cement_psd.csv` is now actually written (it never was — the code called a
   VCCTL-template method absent from THAMES). Feeds ITZ width and the Effective
   Moduli panel's Concelas input.

All five were verified by Jeff in dev mode, and 1 + version were re-verified in
the packaged mac `.app`.

## Windows build steps

```bash
git fetch --tags && git checkout v1.0.0-alpha.3.1
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Expected output: `THAMES-1.0.0-alpha.3.1-win64-setup.exe` (alpha-3's was 627 MB).

**Cautions**

- **Do NOT rebuild the C++ backend.** Ship the same `bin\*.exe` alpha-3 shipped.
  If the Windows tree's `thames.exe` / `micgen.exe` differ from alpha-3's, stop
  and reconcile before publishing — the patch's premise is unchanged engines.
  (Specifically: do not pick up submodule `0343374`, the Session 70 water-
  conservation fix. That is deliberately held for a later release because it
  changes simulation results.)
- Use the `pyinstaller` inside the project venv, not a system/Homebrew-style one
  (the Session 67 trap: a foreign pyinstaller silently produces a bundle missing
  PIL/scipy/matplotlib).
- Working directory on Windows must be `C:\Users\jwbullard\Desktop\foo\THAMES`,
  not `C:\Users\jwbullard\THAMES` (Session 33).
- AppId in `thames-windows.iss` is unchanged, so testers upgrade in place; user
  data lives in `%LOCALAPPDATA%\THAMES\` and the uninstaller only removes
  `{app}` (verified 2026-09-23).
- Version strings already bumped in three places: `app_info.py`,
  `installer/thames-windows.iss` (version + display), and the macOS BUNDLE block
  of `thames-windows.spec`.

## Suggested smoke test before publishing

Install over the existing alpha-3, then:
1. About dialog shows `1.0.0-alpha.3.1`.
2. Mix Design: type a fine-aggregate mass without choosing an aggregate — the
   named warning should appear; "Create Mix" should refuse with a dialog.
3. Select aggregates, generate a microstructure: the progress bar should climb
   through "Placing particles (N %)", and `cement_psd.csv` should appear in the
   operation folder.

## Publishing

Create the GitHub release at tag `v1.0.0-alpha.3.1` with
`release-notes-alpha-3.1.md` as the body, prepend a `### Downloads` section
naming both artifacts (Windows installer + macOS zip, with first-launch
guidance), and upload both files. Do not move the `v1.0.0-alpha.3` tag.

## Open items after the release

- Ask NIST / ERDC whether anyone used **Effective Moduli** or **ITZ**: those used
  fallback values in every THAMES version until fix 5. It is the only
  result-affecting item in this patch.
- micgen's JSON progress only emits 1/5/50/65/95/100; the fine-grained placement
  progress goes to the legacy text file (`micgen.c` ~lines 1932, 1984 hardcode
  `micgen_progress.txt`). Fix 4 blends them UI-side; the root fix is to emit
  placement progress as JSON in `micgen.c`, which needs rebuilt binaries on both
  platforms — schedule with the next engine release.
- POST_ALPHA candidate (not yet filed): the UI log reached 248 MB, driven by a
  per-second `STEP_DEBUG` line from `OperationsMonitoringPanel` plus per-keystroke
  DEBUG lines in the Mix Design panel.
- Still queued from Session 70 (mac, backend): step B (count VOID voxels as empty
  capillary pores in the pore-size distribution) — proposal awaiting review in the
  mac session's memory `project_volume_accounting_handoff.md`.

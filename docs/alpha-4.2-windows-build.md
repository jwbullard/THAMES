# Alpha-4.2 Windows build handoff (2026-11-05, Session 87)

Written on macOS for the follow-on Windows session. Project memory is keyed to
the working-directory path, so the Windows session will **not** see the mac
session's memories; this file carries everything needed.

## Status

| Item | State |
|---|---|
| Source | pushed; `main` at `ddf10f36` or later |
| Version strings | already `1.0.0-alpha.4.2` in `app_info.py`, `installer/thames-windows.iss` (version + display "1.0.0 (alpha 4.2)"), and the macOS block of `thames-windows.spec` |
| Backend | **unchanged**: submodule `6e49f9a` = THAMES-Hydration 6.0.0, the same as alpha-4.1 |
| macOS artifact | built, smoke-tested, uploaded to the draft: `THAMES-1.0.0-alpha.4.2-macOS.zip`, 675,538,545 bytes, SHA-256 `303180c827332c6b927636c1a7845013812927bd32eb9c1f54ce76b6a90fa0e2` |
| GitHub release | **draft** prerelease "THAMES 1.0.0-alpha.4.2" (macOS zip + notes). No tag until publish |
| Windows installer | to build (this session) |
| Release notes | `release-notes-alpha-4.2.md` (Jeff-edited); Windows size says "size TBD" |

## What alpha-4.2 is

A UI-only patch over alpha-4.1; the full list is in `release-notes-alpha-4.2.md`
and the triage at the top of `docs/UI-Issues.md`. The one change that affects
results: hydrotalcite and zeolite P were entered as two phases (fixed in
`simparams_service.py`). Everything else is Python UI code with no platform
branches, except that F1 / User Manual opening on macOS now uses `open`
(Windows path unchanged).

## Windows build steps

Unlike alpha-4.1, **the backend does not need rebuilding**: alpha-4.1's
`thames.exe` / `micgen.exe` (6.0.0, `6e49f9a7`) are what alpha-4.2 ships.

```bash
./pre-session-sync.sh
git submodule update --init               # submodule must stay at 6e49f9a
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Expected output: `dist\THAMES-1.0.0-alpha.4.2-win64-setup.exe` (alpha-4.1's
was 623,513,515 bytes).

**Check the backend before packaging.** Run any short hydration with
`bin\thames.exe` and open its `Result\run_metadata.json`:
`thames_backend.version` must be `6.0.0` and `git_hash` `6e49f9a7`. If
`bin\` is missing or stale, run `./build-windows.sh clean` first (the submodule
is at `6e49f9a`, so the result is the same backend).

**Cautions**

- Use the `pyinstaller` inside the project venv, not a system one (Session 67:
  a foreign pyinstaller silently produces a bundle missing PIL/scipy/matplotlib).
- Working directory must be `C:\Users\jwbullard\Desktop\foo\THAMES`, not
  `C:\Users\jwbullard\THAMES` (Session 33).
- AppId in `thames-windows.iss` is unchanged, so installs upgrade in place;
  user data in `%LOCALAPPDATA%\THAMES\` is untouched.
- Several edited Python files are CRLF; the build doesn't care, but don't let
  an editor convert them if anything needs a fix here.

## Smoke test before copying the installer back

Install over the existing alpha-4.1, then:

1. Home page bottom-right corner and Help -> About show **1.0.0-alpha.4.2**.
2. **Scroll guard (new, first time on Windows):** rest the pointer on a number
   field or drop-down (e.g. Edit Kinetics for Alite, k2 = 0.0500) and scroll:
   the page moves, the value stays. Typing and the arrow buttons still work.
3. ≡ Tools and View menu items open the pages they name; F1 opens the manual
   section for the current page (check Hydration and the pages after it).
4. View -> Fullscreen, then Fullscreen again: the window returns to normal.
5. Hydration -> Load from previous hydration operation, pick a
   `HydrationOf-...` run: the locked top list holds only the starting
   microstructure's phases (no CSHQ, Portlandite, ettringite).
6. Operations: delete a throwaway operation: "Operation deleted successfully" appears.
7. Pozzolanic cement type does not check glass phases, Sfume or Mullite.
8. A short hydration with **hydrotalcite** checked completes; the 3D viewer's
   Phase Data has no unnamed extra phase; `run_metadata.json` reports backend
   6.0.0 / `6e49f9a7`.

## Publishing (back on the Mac; Windows has no `gh`)

Copy the installer to the Mac's `dist/` and record its size and SHA-256 here.
On the Mac:

1. `gh release upload v1.0.0-alpha.4.2 dist/THAMES-1.0.0-alpha.4.2-win64-setup.exe`
2. Replace "size TBD" in the Windows Downloads line, in the release body and
   in `release-notes-alpha-4.2.md`.
3. Publish (`gh release edit v1.0.0-alpha.4.2 --draft=false`), which creates
   tag `v1.0.0-alpha.4.2` on `main`. Keep it a prerelease. No backend tag
   (backend unchanged; `v6.0.0` already at `6e49f9a`).
4. **After** publishing (Jeff's decision, 2026-11-05), amend alpha-4.1's
   release body: insert the block below under its Known Limitations, after
   the line "Limitations 13 and 14 are fixed in this release (see above)."
   Only the body changes (`gh release edit v1.0.0-alpha.4.1 --notes-file
   <edited body>`); tag and assets untouched. Jeff approved this text.

```
  15. **Hydrotalcite and zeolite P are entered twice.** Selecting either as
      a hydration product puts the same phase into the simulation under two
      phase numbers, and both are filled, so the amount of that product is
      probably doubled. Do not select them in this version; fixed in
      1.0.0-alpha.4.2.

  16. **Limestone mixes can stop after a few hours** with a chemical
      equilibrium failure when `SO4_CO3_AFt` is checked (the default for the
      Limestone cement type) while calcite is under thermodynamic control and
      gypsum or bassanite under kinetic control. Workaround: uncheck
      `SO4_CO3_AFt`.

  17. **Calcite under kinetic control can make a run slow and noisy.**
      Workaround: leave calcite under thermodynamic control.
```

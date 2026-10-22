# Alpha-4.1 Windows build handoff (2026-10-22, Session 86)

Written on macOS for the follow-on Windows session. Project memory is keyed to
the working-directory path, so the Windows session will **not** see the mac
session's memories; this file carries everything needed.

## Status

| Item | State |
|---|---|
| Source | pushed; `main` at `78767261` or later (release notes committed) |
| Version strings | already `1.0.0-alpha.4.1` in `app_info.py`, `installer/thames-windows.iss` (version + display "1.0.0 (alpha 4.1)"), and the macOS block of `thames-windows.spec` |
| Backend | submodule `6e49f9a` = THAMES-Hydration **6.0.0** (alpha-4 shipped `243c616`, 5.2.0) |
| macOS artifact | built and uploaded to the draft: `THAMES-1.0.0-alpha.4.1-macOS.zip`, 675,250,874 bytes, SHA-256 `04707cf638e31f5c21b4b43c07fd6c396ed963f4a284f6359f256a30ebe7d4c1` |
| GitHub release | **draft** prerelease "THAMES 1.0.0-alpha.4.1" exists (macOS zip + notes attached). No tag yet; it is created on publish |
| Windows installer | **to be built in this session** |
| Release notes | `release-notes-alpha-4.1.md` (in repo, Jeff-edited, final) |

## What alpha-4.1 is

A small patch over alpha-4. Simulation numbers are unchanged: on the Ca11mM
smoke fixture all 33 output files matched alpha-4 byte for byte, except that
`_CSH.csv` gains one new last column, `GelPorosityAllen`. Changes:

1. New banner on the home page, new application icon (window, About dialog,
   `icon.ico` for the exe and installer, `icon.icns` for macOS), shorter
   home-page tagline.
2. The home page's bottom-right version label read "v10.0.0" (VCCTL leftover);
   it now comes from `APP_VERSION`.
3. Stop on the Operations page now writes `"exit_reason": "Stopped by user"`
   into `Result/run_metadata.json` (alpha-4 Known Limitation 13).
4. Hydration page Resolution field removed (alpha-4 Known Limitation 14).
5. Final time in hours was silently capped at 365; the cap is now 365 days in
   whichever unit is chosen.
6. Backend: trailing `\r` stripped from file names read from `input.in`
   (Windows-authored operation folders now run on macOS/Linux); version 6.0.0;
   `GelPorosityAllen` column.

## Windows build steps

Unlike alpha-3.1, **the backend must be rebuilt**: the installer has to ship
6.0.0, not the alpha-4 `thames.exe`.

```bash
./pre-session-sync.sh                     # first real run under MSYS2 (see cautions)
git submodule update --init               # submodule should be at 6e49f9a
./build-windows.sh clean                  # rebuilds thames.exe and micgen.exe
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Expected output: `THAMES-1.0.0-alpha.4.1-win64-setup.exe` (alpha-4's was
about 628 MB).

**Check the backend before packaging.** Run the smoke fixture or any short
hydration with the freshly built `bin\thames.exe` and open its
`Result\run_metadata.json`: `thames_backend.version` must be `6.0.0` and
`git_hash` must be `6e49f9a7`. If it says `5.2.0` or `243c6165`, the build used
a stale tree; stop and fix before running Inno Setup.

**Cautions**

- **The sync scripts were converted from CRLF to LF in Session 83**, and
  `.gitattributes` now pins root-level `*.sh` to LF. This is the first real
  run of `pre-session-sync.sh` under MSYS2 since then. It should work (the
  build scripts were already LF), but if it misbehaves, do its steps by hand:
  backup branch, `git pull --rebase`, `git submodule update`.
- Use the `pyinstaller` inside the project venv, not a system one (Session 67:
  a foreign pyinstaller silently produces a bundle missing PIL/scipy/matplotlib).
- Working directory on Windows must be `C:\Users\jwbullard\Desktop\foo\THAMES`,
  not `C:\Users\jwbullard\THAMES` (Session 33).
- AppId in `thames-windows.iss` is unchanged, so installs upgrade in place;
  user data in `%LOCALAPPDATA%\THAMES\` is untouched.
- The banner is loaded at the monitor's scale factor
  (`main_window.py::_create_home_tab`); this has only been seen on a Mac
  Retina display. Check it looks sharp and correctly sized on Windows.

## Smoke test before copying the installer back

Install over the existing alpha-4, then:

1. Home page: new banner, tagline "An integrated cement hydration simulation
   package using the GEMS3K library", and **v1.0.0-alpha.4.1** in the
   bottom-right corner.
2. Help -> About: `1.0.0-alpha.4.1` and the new tower logo.
3. Taskbar, Start menu and the installer itself show the new teal tower icon.
4. Hydration page: no Resolution field; set the final-time unit to hours,
   type 672, tab away; it must stay 672.
5. Start a short hydration, press Stop: the run disappears from the process
   list, the operation shows Cancelled, and its `Result\run_metadata.json`
   reads `"exit_reason": "Stopped by user"`.
6. A completed hydration's `Result\run_metadata.json` reports backend 6.0.0,
   `6e49f9a7`; its `_CSH.csv` ends with a `GelPorosityAllen` column.

## Publishing (back on the Mac; Windows has no `gh`)

Copy `THAMES-1.0.0-alpha.4.1-win64-setup.exe` to the Mac's `dist/`, and record
its size and SHA-256 here or in the session. On the Mac:

1. Upload the installer to the existing draft:
   `gh release upload v1.0.0-alpha.4.1 dist/THAMES-1.0.0-alpha.4.1-win64-setup.exe`
   (find the draft with `gh release list`; its temporary URL is
   `untagged-...` until publish).
2. Add the sizes to the two Downloads lines in the release body.
3. Publish (`gh release edit v1.0.0-alpha.4.1 --draft=false`), which creates
   tag `v1.0.0-alpha.4.1` on `main`. Keep it a prerelease.
4. Tag the backend `v6.0.0` at `6e49f9a` and push the tag, as was done for
   alpha-4 (`v5.2.0` at `243c616`).
5. The tutorial videos' Ep 2 end card points at `/releases`; note that
   `/releases/latest` skips prereleases.

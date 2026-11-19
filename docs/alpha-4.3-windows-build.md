# Alpha-4.3 Windows build handoff (2026-11-18, Session 88)

## REBUILD 2026-11-19: replace the published 4.3 assets (do this first)

alpha-4.3 was published 2026-11-19 (tag at `ad4f2da4`). Jeff decided to fold one
display-only change into it and **replace the assets in place** (same version, no
bump; each asset had 1 download, Jeff's own). Results cannot change.

What changed (commit after `4d91c4d3`, see `git log`):

- **Mix Design page:** under each aggregate source dropdown, a small green italic
  line shows the aggregate's specific gravity, bulk modulus and shear modulus
  (`mix_design_panel.py`, `_update_aggregate_properties_label`). Missing values
  show the fallback Elastic Moduli uses, marked "(default)".
- **Seed database:** the stray editable aggregate `MA107-6-fine_copy_2` removed
  (new installs only; existing users keep theirs).

Steps on Windows:

```bash
./pre-session-sync.sh                     # main must include the commit above
git submodule update --init               # submodule stays at 6e49f9a
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

No backend rebuild and no version change. Smoke test (install over the current
4.3): About still says 1.0.0-alpha.4.3; Mix Design -> pick a fine and a coarse
aggregate: the green line appears under each dropdown with the values, and the
Grading... button stays level with the dropdown; choosing the placeholder clears
the line. Then copy `dist\THAMES-1.0.0-alpha.4.3-win64-setup.exe` to the Mac's
`dist/` and record its size and SHA-256 below. On the Mac: upload both assets with
`--clobber`, move the tag, add the dated note to the release body (asking Jeff
before each GitHub change).

| New Windows installer | built 2026-11-19 from `main` at `6ca490f2`, smoke-tested (passed): `THAMES-1.0.0-alpha.4.3-win64-setup.exe`, 623,551,248 bytes, SHA-256 `bf6d1f340b1054f733f50cfb7285c38bd3ccb247c2042a8acff5aa772036b066`. Backend not rebuilt (6.0.0, `6e49f9a7`). Copy to the Mac's `dist/` |
|---|---|
| New macOS zip | built 2026-11-19 from `6ca490f2` + notes, smoke-tested (launch on scratch HOME, 6 aggregates, all 2026 migrations): 673,834,589 bytes, SHA-256 `a9973c6bd2036c5fa01bd64b29a86553ebf24bb6c61fc1c6d419d5ca03df0fba` |

Written on macOS for the follow-on Windows session. Project memory is keyed to
the working-directory path, so the Windows session will **not** see the mac
session's memories; this file carries everything needed.

## Status

| Item | State |
|---|---|
| Source | pushed; `main` at `563d949a` or later. **`563d949a` is required** (see "Migration fix" below) |
| Version strings | already `1.0.0-alpha.4.3` in `app_info.py`, `installer/thames-windows.iss` (version + display "1.0.0 (alpha 4.3)"), and the macOS block of `thames-windows.spec` |
| Backend | **unchanged**: submodule `6e49f9a` = THAMES-Hydration 6.0.0, the same as alpha-4.1 and 4.2 |
| macOS artifact | built, smoke-tested, uploaded to the draft: `THAMES-1.0.0-alpha.4.3-macOS.zip`, 673,832,469 bytes, SHA-256 `2d218c10751bcb8035683b4636709226574bf7ab6c1d9520fddc45016b4dee8e` |
| GitHub release | **draft** prerelease "THAMES 1.0.0-alpha.4.3" (macOS zip + notes). No tag until publish |
| Windows installer | built 2026-11-18 from `main` at `8342ab81`, smoke-tested (all checks passed): `THAMES-1.0.0-alpha.4.3-win64-setup.exe`, 623,537,421 bytes, SHA-256 `5ad06be274d83d2a18139bf29a9b38ebc6350a1e72fa054d5155ca1a574b4370`. Backend not rebuilt (`bin\` = 6.0.0, `6e49f9a7`, built 2026-10-22). Migration check done separately: the installed app, run with `LOCALAPPDATA` pointed at a scratch copy of a September database, applied `20260827_01` and all four `20261117_*` at its own startup (Jeff's real database already had them, applied at 15:30 by an unidentified source before the install, so it could not show this). Copy to the Mac's `dist/` |
| Release notes | `release-notes-alpha-4.3.md` (Jeff-edited); sizes filled in (Windows 624 MB, macOS 674 MB) |
| Known Limitations for published pages | `release-notes-KL-amendments-alpha-4.3.md` is an **untracked Mac-only draft**; applied from the Mac after publishing. Nothing to do on Windows |

## What alpha-4.3 is

A UI and data patch over alpha-4.2 (full list in `release-notes-alpha-4.3.md`,
narrative in `docs/session88_summary.md`). It changes results through the UI:
log-normal PSDs were discretized wrongly, four VCCTL cements get their measured
PSDs, the C-33 / #57 grading templates are corrected, Elastic Moduli now uses the
mix's applied grading, the real ITZ width and SG-based volume fractions. The
grading editor takes cumulative % passing. Operation names get `-01`, `-02`
instead of overwriting. No platform branches in any of it.

### Migration fix (ship-blocker found during the mac build)

`MigrationManager.__init__` used to `mkdir` an unused `migration_scripts`
folder next to the module. Inside a PyInstaller bundle that fails, the
constructor raises, and **no database migration has run in any packaged
release since alpha-3** (it worked only from source). Fixed in `563d949a`.
alpha-4.3's six database changes (four `20261117_*` plus the alpha-3
`20260824_01` and `20260827_01`) only reach users who upgrade in place if the
installer is built from that commit.

## Windows build steps

The backend does not need rebuilding: alpha-4.1's `thames.exe` / `micgen.exe`
(6.0.0, `6e49f9a7`) are what alpha-4.3 ships.

```bash
./pre-session-sync.sh
git log --oneline -1                      # must be 563d949a or later
git submodule update --init               # submodule must stay at 6e49f9a
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Expected output: `dist\THAMES-1.0.0-alpha.4.3-win64-setup.exe` (alpha-4.2's
was 623,568,930 bytes).

**Check the backend before packaging.** `bin\` must hold 6.0.0 / `6e49f9a7`
(a short hydration's `Result\run_metadata.json`: `thames_backend.version`,
`git_hash`). If `bin\` is missing or stale, run `./build-windows.sh clean`.

**Cautions**

- Use the `pyinstaller` inside the project venv, not a system one (Session 67).
- Working directory must be `C:\Users\jwbullard\Desktop\foo\THAMES`, not
  `C:\Users\jwbullard\THAMES` (Session 33).
- AppId unchanged, so installs upgrade in place; user data in
  `%LOCALAPPDATA%\THAMES\` is untouched.
- Several Python files are CRLF; don't let an editor convert them.
- Any check that imports app modules from source (`python -c "from app...`)
  runs the migrations on the **real** database. Set a scratch
  `LOCALAPPDATA` for such checks.

## Smoke test before copying the installer back

**Back up `%LOCALAPPDATA%\THAMES\database\` first**, then install over the
existing alpha-4.2 (the in-place upgrade is the case that matters), and:

1. Home page and Help -> About show **1.0.0-alpha.4.3**.
2. **Migrations ran.** `%LOCALAPPDATA%\THAMES\logs\thames.log` shows no
   "migration_scripts" / "No such file or directory" error, and the
   `migrations` table holds `20261117_01` .. `_04` (plus `20260824_01` and
   `20260827_01` if this database never had them):
   `sqlite3 thames.db "select version from migrations order by version"`.
3. Materials: `ustype1` opens as **Custom** PSD with a table; "σ of ln(d)"
   label on a Log-Normal material. Duplicate a material, change the copy's
   PSD, reopen the original: unchanged.
4. Mix Design -> Grading…: entry is cumulative % passing; the coarse table has
   No. 8 and No. 16; templates "ASTM C-33 Fine Aggregate" and "ASTM #57 Stone"
   plot as sensible S-curves; Import and Export of a `.gdg` work and the file
   dialog closes.
5. A small mortar (any cement + fine aggregate, Grading… -> Apply, save):
   microstructure, short hydration, then Elastic Moduli. The form is
   read-only; running it twice on the same microstructure gives the second run
   `-01`. Effective Moduli shows an ITZ width that is not 10 μm; ITZ Analysis
   shows nonzero layers.
6. `run_metadata.json` reports backend 6.0.0 / `6e49f9a7`.

## Publishing (back on the Mac; Windows has no `gh`)

Copy the installer to the Mac's `dist/` and record its size and SHA-256 here.
On the Mac:

1. `gh release upload v1.0.0-alpha.4.3 dist/THAMES-1.0.0-alpha.4.3-win64-setup.exe`
2. Replace "SIZE MB" in the Windows Downloads line, in the release body and in
   `release-notes-alpha-4.3.md`.
3. Publish (`gh release edit v1.0.0-alpha.4.3 --draft=false`), creating tag
   `v1.0.0-alpha.4.3` on `main`. Keep it a prerelease. No backend tag.
4. Then apply `release-notes-KL-amendments-alpha-4.3.md` (A-G) to the
   alpha-2 .. alpha-4.2 pages, one page at a time, Jeff approving each.

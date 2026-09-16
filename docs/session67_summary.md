# Session 67 — 2026-09-16

**Focus.** Build and ship the macOS artifact for alpha-3, following the pattern established for alpha-2 (upload as additional asset to the existing v1.0.0-alpha.3 release page, do not move the tag). Also uncovered and filed three release-engineering surprises that cost time.

**Commit.** `0c97a0db` — Session 67: alpha-3 mac artifact shipped + spec version bump + build-env POST_ALPHA entries. Pushed.

---

## Where we started

- On mac. `main` was at `3f3543de` (my S65 wrap-up) — 5 commits behind `origin/main` because Session 66 (Sep 16, Windows) shipped the alpha-3 Windows installer and did the release-notes polish while I was absent.
- Windows already shipped: `THAMES-1.0.0-alpha.3-win64-setup.exe` (627 MB) live at the new `v1.0.0-alpha.3` release page as of Sep 16, 14:38 CDT. Release-notes.md also uploaded. No mac asset yet.
- Jeff's task for this session: build the mac artifact and upload it to the same release page. Do not move the tag.

## Pre-session sync

Ran the individual steps (per standing preference). Fetch + fast-forward pull picked up 5 new commits from S66; created `pre-s67-backup` branch first; submodule tip unchanged (still `f795965` from S65 — S66 was pure Python-side changes). Read `project_nist_patch_state.md` at Jeff's mid-turn suggestion for extra context — that memory is 22 days old and describes the alpha-2.1 hotfix ship state, useful as background for the release-page-asset pattern.

## S66 catch-up (from commit range `05bab429..HEAD`, since no `session66_summary.md` was written)

Five commits from Jeff's Windows session on Sep 16:

- **`05bab429` Session 66: version bump to 1.0.0-alpha.3.** `src/app/resources/app_info.py` APP_VERSION + `installer/thames-windows.iss` MyAppVersion bumped. Windows installer built and uploaded to the NEW `v1.0.0-alpha.3` release page (not additional-asset on alpha-2 like the 2.1 hotfix was — alpha-3 is a full release step). In-place upgrade over 1.0.0-alpha.2.1 verified: About dialog shows new version; cem151-fa-1 microstructure gen + 28-day hydration both clean with the S62 clamp firing 856 times.
- **`71609038` Alpha-3 KL#2 promoted to Thermodynamic-sulfates workaround.** S66 smoke test hit the Arcanite depletion + dt collapse around cycle 10,200 (S62 clamp kept run alive but throttle persisted). Jeff's fix: pencil-edit Arcanite from Standard to Thermodynamic in Hydration Products tree. Verified: same simulation completes in ~2 min wall. Release-notes KL#2 rewritten with pencil-edit as "Recommended workaround"; POST_ALPHA filed to change the default kinetic type.
- **`e1f93f77` Three thames.log cosmetic items filed.** ThemeManager CSS parse error at `<data>:309:39`, two missing Carbon icons at size 48 (48-database, 48-statistics), mixed VCCTL/THAMES/app logger prefixes. Pre-existing; not shipping blockers.
- **`d8e06d48` Release-notes polish.** Typos (bewhavior, becen suffixed, C3s), renumbered Fixed section (duplicate "2." + skip 12→14 fixed to unbroken 1-15), cross-refs re-anchored, KL#7 qualified to fly-ash-only after S66 Windows Portland-only byte-parity confirmation.
- **`6991f30f` Alpha-3 release notes: strip "working draft" preamble line.**

## macOS build sequence

**Backend rebuild** via `./build-macos.sh clean`. Compiled cleanly:
- `bin/thames` 2.3 MB, `bin/micgen` 177 KB, `bin/libpng16.16.dylib` 203 KB (Homebrew-bundled via `install_name_tool` @rpath rewrite, ad-hoc code-signed).
- Generated `version.h` embeds `THAMES_GIT_HASH "f7959659"` (matches submodule tip `f795965`), build date `2026-09-16T19:55:38Z`, AppleClang 21.0.0, `-O2 -std=c++17`. Every alpha-3 mac op's `run_metadata.json` will carry correct provenance.

**Spec-file drift caught + fixed** (Cross-Platform Safety Protocol paid off). Reading `thames-windows.spec` before invoking pyinstaller surfaced that lines 223-224 still had `'CFBundleVersion': '1.0.0-alpha.2'` / `'CFBundleShortVersionString': '1.0.0-alpha.2'` — both stale. One-line-per-string edit to `1.0.0-alpha.3`. Change is inside `if IS_MACOS:` so Windows path is untouched. Filed POST_ALPHA to source both strings from `src/app/resources/app_info.py::APP_VERSION` so this doesn't drift again.

**PyInstaller — three false starts before success:**

1. **First attempt** (Homebrew `/opt/homebrew/bin/pyinstaller`): BUNDLE built but the harfbuzz post-hook errored with `Expected PyInstaller-bundled PIL harfbuzz at .../PIL/__dot__dylibs/libharfbuzz.0.dylib, not found`. Investigation: no PIL anywhere in the bundle. Root cause: Homebrew's pyinstaller runs against its own isolated Python `/opt/homebrew/Cellar/pyinstaller/6.22.3/libexec/bin/python` — no THAMES deps visible. The many "Hidden import 'scipy.stats' not found" / "'markdown.extensions.toc' not found" errors earlier in the log were the same story: PyInstaller couldn't see PIL, scipy, matplotlib, pyvista, gi, etc.

2. **Second attempt** (installed `pyinstaller` into thames-env via `pip install pyinstaller`, ran with venv activated): Now sees deps correctly. But died at Analysis with `Could not find GIR file 'GLib-2.0.gir'; check XDG_DATA_DIRS` and `ERROR: Unable to find '.../Gio-2.0.typelib' when adding binary and data files`. Homebrew places these under `/opt/homebrew/share/gir-1.0/` and `/opt/homebrew/lib/girepository-1.0/`, but neither `XDG_DATA_DIRS` nor `GI_TYPELIB_PATH` had those paths.

3. **Third attempt** (venv-activated + full env exports):
   ```
   export XDG_DATA_DIRS=/opt/homebrew/share:/usr/local/share:/usr/share
   export GI_TYPELIB_PATH=/opt/homebrew/lib/girepository-1.0
   export PKG_CONFIG_PATH=/opt/homebrew/lib/pkgconfig
   export DYLD_LIBRARY_PATH=/opt/homebrew/lib
   ```
   Analysis completed (scipy hooks, matplotlib hooks, pandas, PIL all present). BUNDLE succeeded. Harfbuzz post-hook succeeded (PIL bundled → PIL harfbuzz at expected path → swapped with Homebrew's CoreText-capable libharfbuzz.0.dylib → bundle re-signed).

**Package + upload.** `ditto -c -k --keepParent --rsrc dist/THAMES.app dist/THAMES-1.0.0-alpha.3-macOS.zip` → 649 MB / 680,896,478 bytes. SHA-256 `57c61d65e4442c450b9364ed0e368556c2baca4958fbd300e445156c1388b25b`. `gh release upload v1.0.0-alpha.3 dist/THAMES-1.0.0-alpha.3-macOS.zip` — clean upload, tag untouched.

**Release body updated** with a new `### Downloads` section prepended (between the preamble and the "Fixed since alpha-2" heading) naming both platform artifacts, first-launch guidance, and macOS minimum. Local `release-notes-alpha-3.md` file NOT touched — the Downloads section lives only in the GitHub release body, since the file is content-focused and the Downloads section is release-page metadata.

## Verifications done

- **Info.plist stamped correctly** — `plutil -p` confirms `CFBundleVersion` / `CFBundleShortVersionString = 1.0.0-alpha.3`.
- **Backend binaries in bundle** — `THAMES.app/Contents/Resources/bin/` contains `thames`, `micgen`, `libpng16.16.dylib`.
- **codesign --verify --deep --strict** passes (no output = success).
- **Bundle launcher architecture** — Mach-O 64-bit arm64 (Apple Silicon).
- **Release-page state after upload** — 3 assets present (win64 exe, mac zip, release-notes.md); tag `v1.0.0-alpha.3` unchanged.

**Not done** (Jeff to do if desired): live GUI smoke test by unzipping and launching. Skipped by design — was doing this over a running mac session and didn't want to pop windows on Jeff's screen without asking. Everything mechanically verifiable was verified.

## POST_ALPHA entries filed

1. **macOS .app version drift — Info.plist strings should source from APP_VERSION.** Prevent the one-line-per-release manual bump that has now happened at least twice (alpha-2 → alpha-3, and probably alpha-1 → alpha-2). Import APP_VERSION at spec-file top and use it; safe cross-platform (app_info.py is pure Python).
2. **pyinstaller must live inside thames-env, not Homebrew — document + enforce.** Add pyinstaller to requirements.txt (or split runtime/build) and update `build-macos.sh` / `build-windows.sh` to explicitly invoke `thames-env/bin/pyinstaller` with the four GTK env exports so nobody has to remember them.

Both entries include the specific commands / paths / file locations needed to implement, so future maintenance sessions can pick them up cold.

## What alpha-3 macOS zip ships (for the record)

Everything from `main` at `0c97a0db` + submodule at `f795965`:
- S46 3D viewer color-button fix + kinetic-editor save fix.
- S47 Mix Design 32³ fix.
- S55 mass-balance fix (`commitSolidICTransfer`).
- S56 C3S ln K correction in DCH.
- S57 C3A ln K correction in DCH.
- S58 provenance sidecar (`run_metadata.json`) + F1/F2 crash-provenance + Load Operation microstructure restore.
- S59 glass-phase (am) rename + Windows shell-out portability + electrolyte-fixed bias fix.
- S61-S62 hotfix bundle: `-lws2_32` link, micgen triple-fix, glass-phase migration, DC-depletion clamp, zero-content correlation-file skip.
- S63 ServiceContainer migration wire-up.
- S64 aggregate-combo placeholder default + phase-connectivity fix + hydrotalcite dedup + orphan-aggregate cleanup migration.
- S65 shell-diffusion doc + transport code-doc cleanup.
- S66 Thermodynamic-sulfates KL#2 workaround (via release-notes; the default is still Standard, documented workaround for testers who hit late-age Arcanite depletion).
- S67 (this session): CFBundleVersion bump.

## Memory updates

- `project_nist_patch_state.md` — the alpha-2.1 hotfix is now superseded by the full alpha-3 release (both platforms). Marking superseded so future sessions don't chase stale distribution guidance.
- `project_alpha2_macos_followup.md` — the "defer mac hotfix to alpha-3" decision from S63 has now been executed. Marking done.

## Working-tree state at wrap-up

Clean, pushed. Nothing pending after this summary + CLAUDE.md + memory-update commit.

# Session 45: macOS Alpha-2 Build, Public Cross-Platform Release

**Date:** May 2, 2026
**Platform:** macOS (Darwin 25.4.0, arm64)

## Overview

Brought the macOS packaging up to parity with the Windows alpha-2 release Session 44 had already shipped. The repo is now public on GitHub and the v1.0.0-alpha.2 release page carries artifacts for both platforms — first cross-platform public release of THAMES.

No runtime code changed in this session. All work was build infrastructure (PyInstaller spec, build script, app icon) plus the artifact + release upload. The macOS .app's runtime behavior is identical to Windows alpha-2 because the Python and C++ source at the v1.0.0-alpha.2 tag is the same on both.

## The Plan (8 Steps)

After pre-session sync of Sessions 42-44 (six commits, fast-forward), an 8-step plan was agreed before any work:

1. Fix macOS spec file (VCCTL paths + DB path)
2. Verify C++ backend is current (`build-macos.sh` if needed)
3. Dev-mode smoke test (`python src/main.py`)
4. Build with PyInstaller
5. Smoke test the bundled `.app`
6. Wrap into zipped `.app`
7. Compose macOS-specific README
8. Move tag, commit, push, `gh release create` with all artifacts

Two plan adjustments emerged during execution: (a) we created a real `icon.icns` rather than deferring the icon — user wanted polish for the alpha; (b) Step 8 became "upload to existing release without moving the tag" once we learned the Windows alpha-2 had already been published manually via the GitHub web UI.

## Step 1: Spec / build script / icon

The cross-platform spec (`thames-windows.spec`, despite the name) had an `IS_MACOS` branch that referenced seven nonexistent paths under `backend/bin/` — direct VCCTL legacy. Replaced with the actual THAMES backend artifacts:

```python
elif IS_MACOS:
    platform_binaries = [
        ('bin/thames', 'bin/'),
        ('bin/micgen', 'bin/'),
        ('bin/libpng16.16.dylib', 'bin/'),
    ]
```

Also bumped `CFBundleVersion` and `CFBundleShortVersionString` from `'10.0.0'` to `'1.0.0-alpha.2'` and added `LSMinimumSystemVersion = '10.14'` and `LSApplicationCategoryType = 'public.app-category.education'` to match what the deleted legacy spec carried.

**Libpng bundling discovery.** `otool -L bin/thames` showed `/opt/homebrew/opt/libpng/lib/libpng16.16.dylib` as a hard dependency — testers without Homebrew would see "dylib not loaded" at first launch. Built the install_name_tool sequence manually first, then added a permanent Step 5 to `build-macos.sh`:

```bash
cp -L "$LIBPNG_SRC" "$LIBPNG_DST"
chmod u+w "$LIBPNG_DST"
install_name_tool -id @rpath/libpng16.16.dylib "$LIBPNG_DST"
codesign --force --sign - "$LIBPNG_DST"
for BIN in "$BIN_DIR/thames" "$BIN_DIR/micgen"; do
    install_name_tool -change "$LIBPNG_SRC" @rpath/libpng16.16.dylib "$BIN"
    if ! otool -l "$BIN" | grep -q "path @loader_path "; then
        install_name_tool -add_rpath @loader_path "$BIN"
    fi
    codesign --force --sign - "$BIN"
done
```

The rpath check is idempotent so repeated `build-macos.sh` runs don't accumulate duplicate `LC_RPATH` entries.

**Icon.** `src/app/resources/icon.icns` did not exist (only `icon.ico` for Windows). Generated from the existing `icons/thames-icon.png` (1036×1036 RGBA) using `sips` at the 10 standard iconset sizes (16/32/64/128/256/512/1024 plus @2x retina) and `iconutil -c icns`. Lands at the path the spec's `os.path.exists` check already looks at, so no spec change needed for the icon.

**Deletion of legacy `thames-macos.spec`.** A separate spec file existed but was full of VCCTL legacy: executable name `vcctl`, `vcctl.db` references, `vcctl-docs/site` MkDocs paths, the wrong icon. None of it had been used since the project pivoted off VCCTL — `build-macos.sh` only handles the C++ side and PyInstaller is invoked manually with `thames-windows.spec`. Deleted to remove a future-confusion source.

## Step 2: Backend verify

`./build-macos.sh` ran clean — micgen recompiled (one source file), thames was already up to date. The new Step 5 bundled libpng correctly. `./bin/thames --help` exited 0 with `@rpath/libpng16.16.dylib` resolving via `@loader_path` to the bundled copy.

## Step 3: Dev-mode smoke test

User passed all six checklist items: About dialog (version 1.0.0-alpha.2, ALPHA banner, Texas A&M renders cleanly), Help menu (User Guide / Getting Started / Troubleshooting all open in browser at correct sections), stop/cancel persistence, orphan-aggregate dialog (preempted by Session 42's `_apply_aggregate_gating()` — confirmed working as designed), and Materials/Mix Design panels populated.

## Step 4: PyInstaller build (and the harfbuzz crisis)

`thames-env` had all the runtime deps but not PyInstaller. Installed PyInstaller 6.20.0 into the venv (Homebrew's pyinstaller would use a different Python and not see the deps).

Build itself ran in ~2 minutes and produced `dist/THAMES.app` (1.1 GB), ad-hoc signed, version `1.0.0-alpha.2`. Binaries landed at `Contents/Frameworks/bin/` (PyInstaller's macOS convention) and the code's `sys._MEIPASS / "bin"` lookup resolves there correctly.

Then the bundle silently failed to launch — no error dialog, nothing. Direct invocation of `Contents/MacOS/THAMES` from Terminal printed the actual cause:

```
Failed to load shared library '@loader_path/libgdk-3.0.dylib' referenced by the typelib:
dlopen(...): Symbol not found: _hb_coretext_font_create
  Referenced from: .../libpangocairo-1.0.0.dylib
  Expected in:     .../PIL/__dot__dylibs/libharfbuzz.0.dylib
```

Diagnosed: PyInstaller's PIL hook bundles a minimal `libharfbuzz.0.dylib` built without CoreText support. Pillow's hook ran after the GI hook, and PIL's harfbuzz won the canonical `Contents/Frameworks/libharfbuzz.0.dylib` slot via a symlink chain. Homebrew's `libpangocairo` (collected by the GI hook) was built against Homebrew's harfbuzz which DOES have `_hb_coretext_font_create`, so it expected the symbol — and crashed when dyld returned PIL's harfbuzz.

Fix: replace the single physical PIL harfbuzz file (everything else in the bundle resolves to it via symlinks) with Homebrew's, rewriting install_names from `/opt/homebrew/...` to `@rpath/...` for `libfreetype.6.dylib`, `libglib-2.0.0.dylib`, and `libgraphite2.3.dylib`. All three deps are already in `Contents/Frameworks/` from the GI hook, so the rewritten harfbuzz finds them. Re-codesign the dylib and the parent bundle (deep, ad-hoc).

After the manual fix, the bundle launched cleanly (10-second test launch wrote `~/Library/Application Support/THAMES/database/` with the seed DB before being killed).

**Permanent fix in the spec.** Added a post-BUNDLE block inside `if IS_MACOS:` that runs the install_name_tool + codesign sequence at the end of every PyInstaller build, with explicit error-raises if Homebrew harfbuzz is missing or if PyInstaller's bundle layout shifts in a future release. Comment block in the spec explains why the swap is necessary.

## Step 5: Bundled .app smoke test

User passed all six bundled-app checklist items first try: first-launch extraction completes (~1-2 min for aggregate.tar.gz + particle_shape_set.tar.gz), Materials panel populates with seed data, About dialog correct, Help menu works in browser, end-to-end pipeline (mix → microstructure → quick hydration → elastic) executes, 3D viewer renders OpenGL.

## Step 6: ZIP wrap

Used `ditto -c -k --keepParent --rsrc` (the Apple-recommended tool that preserves resource forks and code-signing metadata; `zip` and Python's `zipfile` would break the codesign). Output: `dist/THAMES-1.0.0-alpha.2-macOS.zip` (621 MB; 44% compression on a 1.1 GB binary-heavy bundle), 28 seconds. Round-tripped through `ditto -x -k` and confirmed `codesign --verify` passes ("valid on disk", "satisfies its Designated Requirement").

## Step 7: macOS tester README

Wrote `dist/THAMES-1.0.0-alpha.2-macOS-README.txt` modeled on the Windows README (Session 44, never committed but still on the GitHub release page). Differs from Windows in install instructions (drag-to-Applications, Gatekeeper bypass via right-click → Open or `xattr -dr com.apple.quarantine`), log paths (`~/Library/Application Support/THAMES/logs/`), and system requirements (macOS 10.14+ Apple Silicon). Known limitations and bug-reporting sections deliberately mirror the Windows README so testers across platforms hear the same caveats.

## Step 8: Public release

Plan revision: the user mentioned the Windows alpha-2 was already published on GitHub (manually, per Session 44's pending list — I'd lost that detail). With a public tag, force-moving it would be bad practice. Switched to **Option A**: commit the macOS build infrastructure as a new commit on `main`, leave the tag where it is, and `gh release upload` the macOS artifacts to the existing release. Defensible because every change in this session was build-tooling only; no Python or C++ runtime changed, so the macOS .app's behavior matches what the v1.0.0-alpha.2 tag represents.

Installed `gh` (Homebrew, 2.92.0) since it wasn't on this machine. User did `gh auth login` with the device-flow browser auth (HTTPS, with Git credential helper enabled). Auth came back with token scopes `gist, read:org, repo, workflow` — `repo` covers release management.

Commit `bbe62bb3` (`macOS alpha-2 build infrastructure`) staged exactly four things:

```
A  src/app/resources/icon.icns
D  thames-macos.spec
M  build-macos.sh
M  thames-windows.spec
```

`.claude/settings.local.json` (local Bash permissions) and `config/preferences.yml` (window position) intentionally excluded.

Push, then `gh release upload v1.0.0-alpha.2 --clobber` with both macOS files. Final asset count on the release page: 5 (3 Windows + 2 macOS). Notes rewritten with both-platform structure (Platforms / Downloads / System requirements / Installation Windows / Installation macOS / Getting Started / Known Limitations / Crash Diagnostics / Reporting Bugs).

Release URL: https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.2

## Side discovery: the 271-hour orphan

Pre-Step-1 inspection of the data dir for the rename-aside test caught a `bin/thames` process running for 11 days, 7 hours, 23 minutes — `HydrationOf-ccr152-concrete`, the same near-depletion-stall hydration that's been logged in `POST_ALPHA_TODOS.md` since Session 41. The DB had been reconciled to `CANCELLED` by Session 41's stop/cancel fix, but the spawned simulator process never received the message and kept running for 11 days. It had grown a `thames.log` to 251 MB in that time. This is exactly the orphan pattern in `POST_ALPHA_TODOS.md` ("Reconciler marks live operations CANCELLED when UI is restarted"); user authorized killing PID 7111 with `kill` (clean SIGTERM, no SIGKILL needed).

The 271-hour runaway was wasting CPU and disk for the entire Session 42-44 Windows work plus the start of this session.

## Data dir handling

User wanted a true clean first-launch experience for Step 5 without losing pre-existing operations. Renamed `~/Library/Application Support/THAMES` to `THAMES.bak` (12 GB) before the bundled-app launch, let the bundle do its first-launch extraction into a fresh `THAMES`, did the smoke test, then discarded the 2.2 GB smoke-test dir and restored `THAMES.bak` to the canonical name. Original 12 GB of operations data fully intact.

## Files Modified (committed)

- `thames-windows.spec` — IS_MACOS binaries swap; macOS BUNDLE version + plist; new post-BUNDLE harfbuzz fix block (~50 lines with error-raises and a multi-paragraph comment explaining why)
- `build-macos.sh` — new Step 5 bundles libpng with install_name_tool + codesign, idempotent rpath check
- `src/app/resources/icon.icns` — new, ~3 MB multi-resolution
- `thames-macos.spec` — **deleted** (was VCCTL legacy boilerplate)

## Files Modified (NOT committed)

- `.claude/settings.local.json` — local Bash permissions accumulated during testing
- `config/preferences.yml` — window position only

## Build Artifacts (in `dist/`)

- `THAMES.app` (1.1 GB) — the source of the zip
- `THAMES-1.0.0-alpha.2-macOS.zip` (621 MB) — distribution artifact
- `THAMES-1.0.0-alpha.2-macOS-README.txt` (4.7 KB) — tester README
- `THAMES/` (PyInstaller intermediate, can be deleted to reclaim ~1.1 GB)

## Verification

- C++ backend: `./bin/thames --help` exits 0 with bundled `@rpath/libpng16.16.dylib`.
- Dev-mode UI: 6/6 smoke tests passed (Step 3).
- PyInstaller bundle: 6/6 smoke tests passed (Step 5), including end-to-end mix → microstructure → hydration → elastic round-trip and 3D viewer.
- ZIP integrity: `codesign --verify` passes after `ditto -c/-x` round-trip.
- GitHub release: 5 assets visible at https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.2.

## Cumulative file changes for Session 45

New: `src/app/resources/icon.icns`, `dist/THAMES-1.0.0-alpha.2-macOS.zip`, `dist/THAMES-1.0.0-alpha.2-macOS-README.txt`, `docs/session45_summary.md`.
Modified: `thames-windows.spec`, `build-macos.sh`, `CLAUDE.md`.
Deleted: `thames-macos.spec`.
Tag: `v1.0.0-alpha.2` (unchanged).
GitHub release: 5 assets (Win .exe + Win .zip + Win README + Mac .zip + Mac README), notes rewritten for both platforms.

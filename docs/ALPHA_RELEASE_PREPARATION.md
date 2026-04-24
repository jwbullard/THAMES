# THAMES Alpha Release Preparation — Windows

Step-by-step recipe for building and packaging the **v1.0.0-alpha.1** release on Windows.
Follow these in order. Each step has a verification check.

**Target version:** `1.0.0-alpha.1` (tag `v1.0.0-alpha.1` already pushed on `main`)
**Working directory on Windows:** `C:\Users\jwbullard\Desktop\foo\THAMES` (NOT `C:\Users\jwbullard\THAMES`)

---

## 1. Sync the repo on Windows

```bash
./pre-session-sync.sh
git fetch --tags                 # pulls v1.0.0-alpha.1
git describe                     # should print v1.0.0-alpha.1
```

**Verify:** `git describe` shows `v1.0.0-alpha.1` (or that plus a few commits if the next session adds fixes).

**LFS:** no new LFS files this session. If any `*.tar.gz` seems truncated, run `git lfs pull`.

---

## 2. Refresh the Python environment

The help viewer work added `markdown` as the only new pip-managed dependency.
Install just that; do **not** run the full `pip install -r requirements.txt`
on Windows — see the note below.

```bash
# In your Windows MSYS2 / native shell, with thames-env-windows activated:
./thames-env-windows/bin/python.exe -m pip install "markdown>=3.4.0"
./thames-env-windows/bin/python.exe -c "import markdown; print('markdown', markdown.__version__)"

# scipy is a runtime dep for Mix Design (log-normal PSD). Install via MSYS2 on Windows:
/c/msys64/usr/bin/pacman.exe -S --noconfirm mingw-w64-x86_64-python-scipy
./thames-env-windows/bin/python.exe -c "from scipy.stats import lognorm; print('scipy OK')"
```

**Verify:** `markdown 3.x.y` and `scipy OK` both print, no errors.

**Why not `pip install -r requirements.txt` on Windows?** `thames-env-windows`
is created with `--system-site-packages` against MSYS2's mingw-w64 Python,
so most requirements (PyGObject, SQLAlchemy, pandas, numpy, pydantic,
PyYAML, Pillow, matplotlib, pyvista 0.36, reportlab, openpyxl, lxml, ...)
are already supplied by `pacman`. Re-running the full requirements file
makes pip try to **upgrade** the MSYS2-supplied packages (e.g. pyvista
0.36 → 0.47), which cascades into source builds of numpy via
meson-python + ninja. MSYS2 does not ship `ninja` by default, so those
builds fail. `markdown` is the only dependency Session 41 actually added,
and MSYS2 doesn't provide it, so installing it alone is sufficient.
See the header comment in `requirements.txt`.

---

## 3. Confirm the C++ backend is up to date

Session 41 **did not** touch the C++ backend. The existing `bin/thames.exe` from Session 39/40 should still work. Quick check:

```bash
# (Windows equivalent of strings(1); PowerShell version:)
Select-String -Path bin/thames.exe -Pattern "ITZModuli","EffectiveModuli","Aggregate surface" -Encoding Byte -ErrorAction SilentlyContinue
# or install `sysinternals strings.exe` and run: strings bin/thames.exe | findstr /C:"ITZModuli"
```

**Verify:** `ITZModuli.csv`, `EffectiveModuli.csv`, and `Aggregate surface position` all appear in the binary.

If the binary is missing any of those, run `./build-windows.sh`. No submodule changes occurred this session, so the build should be incremental and fast.

---

## 4. Smoke test in dev mode

Before packaging, confirm the full stack works end-to-end:

```bash
python src/main.py
```

Run this checklist (10-15 min total):

1. **Help menu** — All three must work:
   - Help → User Guide → browser opens at the top of the rendered manual. Images render. TOC links navigate within the page.
   - Help → Getting Started → browser opens directly at "2. Getting Started" (not the TOC).
   - Help → Troubleshooting → browser opens directly at "11. Troubleshooting".
   - Help → About THAMES → dialog shows version "1.0.0-alpha.1" and tagline ending with "ALPHA pre-release, not for production use". Click Credits — "Texas A&M University" renders correctly (no `<span>` markup visible).

2. **Stop/cancel persistence** — Start any operation, then Stop it. Close the app. Reopen. The operation must show as Cancelled, NOT running. No "starting up" dialog.

3. **Concelas pipeline (optional, slower)** — If time permits, run a small 50³ or 100³ aggregate-bearing hydration to ~1 day, then an elastic calc on the final microstructure. Check `Result/EffectiveModuli.csv` contains Concrete_* and ITZ_* rows and that `Result/ConcelasLog.txt` exists.

4. **Orphan-aggregate dialog** — In Mix Design, select an aggregate with mass = 0 and click Generate Microstructure. Confirm the warning dialog appears before generation starts.

If any of these fail, stop and diagnose before packaging.

---

## 5. Build the installer

```bash
pyinstaller thames-windows.spec --noconfirm
```

The spec is already updated to include:
- `markdown` + its key extensions in `hiddenimports`
- `docs/USER_MANUAL.md` bundled to `docs/` in the app
- `docs/images/` bundled recursively
- `aggregate.tar.gz` and `particle_shape_set.tar.gz` (unchanged from Session 40)

**Verify:** `dist/THAMES/` directory is created. Run `dist/THAMES/THAMES.exe` and repeat the smoke test from Step 4 against the bundled version. Especially confirm Help → User Guide works (the manual renders from the bundled copy, not from the source tree).

If you see "Documentation Not Found," the `datas` section of `thames-windows.spec` didn't bundle the manual — re-check lines around `docs/USER_MANUAL.md`.

---

## 6. Wrap the installer

You have two options:

**Option A — Zip distribution (fast, unsigned):**
```bash
cd dist
Compress-Archive -Path THAMES -DestinationPath THAMES-1.0.0-alpha.1-win64.zip
```

**Option B — MSI/Inno Setup installer (recommended, still unsigned):**
Use Inno Setup 6+ to wrap `dist/THAMES/` into an installer:
- Installer name: `THAMES-1.0.0-alpha.1-setup.exe`
- Install target: `%LOCALAPPDATA%\Programs\THAMES\` (no admin required)
- Start-menu shortcut + desktop shortcut to `THAMES.exe`
- Uninstaller registered in Programs & Features
- Script file: if one doesn't exist yet in the repo, create `installer/thames-windows.iss`

**Signing:** not configured for alpha. Windows SmartScreen will warn alpha testers that the publisher is unknown. Document this in the README (Step 7) so testers know to click "More info → Run anyway."

---

## 7. Prepare the alpha tester README

Create `dist/THAMES-1.0.0-alpha.1-README.txt` alongside the installer with:

```
THAMES 1.0.0-alpha.1 — Alpha Release Notes
=============================================

What is this?
  An early preview of THAMES, a cement hydration simulator with
  multi-scale elastic moduli and concrete-scale homogenization.

Status: ALPHA — NOT FOR PRODUCTION USE
  - May contain bugs, incomplete features, or unexpected behavior.
  - Some long hydration simulations may stall near late ages (see
    "Known Limitations" below).
  - API and file formats may change in later releases without notice.

Installation
  - Windows SmartScreen will warn: "Windows protected your PC."
    Click "More info" then "Run anyway". The installer is not
    currently code-signed; this is expected for alpha.
  - Installs to %LOCALAPPDATA%\Programs\THAMES\
  - Shortcuts added to Start Menu and Desktop.

Getting Started
  After launching, use the Help menu:
    Help -> Getting Started (jumps to the Getting Started section)
    Help -> User Guide      (full manual, ~1,200 lines)
    Help -> Troubleshooting (common issues and fixes)

Known Limitations
  1. Adaptive timestep can collapse to ~0.1 ms/cycle at late ages if a
     sulfate phase (Arcanite, Thenardite) drops to < 10 voxels.
     Workaround: uncheck those phases in the Hydration Products tree
     before a long run.
  2. Loading a 200^3 microstructure in the 3D viewer can use ~5 GB RAM.
     Stay at 100^3 for alpha testing unless you have plenty of memory.
  3. Clicking "Stop and Delete" on a running simulation occasionally
     leaves thames.exe running briefly before it exits. Not harmful.
  4. The micgen tool may report a non-zero exit code even after writing
     all output files successfully. Outputs are still usable.

Reporting Bugs
  Please include:
   - The version string from Help -> About (should say 1.0.0-alpha.1)
   - Steps to reproduce
   - Any .log or exit_status.json files from the affected operation directory

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu
```

---

## 8. Final checklist before distribution

- [ ] Installer built and installed onto a **clean** Windows machine or fresh user profile
- [ ] Version string visible in About dialog matches `1.0.0-alpha.1`
- [ ] "ALPHA pre-release" banner visible in About dialog tagline
- [ ] Manual's title-page version line matches
- [ ] Help menu, concelas, stop/cancel, orphan-aggregate all verified on the clean install
- [ ] README packaged alongside the installer
- [ ] Filename convention: `THAMES-1.0.0-alpha.1-setup.exe` (or `.zip`)
- [ ] Distribution channel decided (direct email? Private GitHub release? Shared Drive link?)
- [ ] Feedback channel documented in README

---

## 9. Mark the tag on GitHub

If you haven't already, promote the `v1.0.0-alpha.1` git tag to a GitHub **pre-release** entry:

1. On GitHub → Releases → Draft a new release
2. Choose tag: `v1.0.0-alpha.1`
3. Release title: `THAMES 1.0.0-alpha.1`
4. Check **"This is a pre-release"**
5. Paste the README text into the description
6. Attach `THAMES-1.0.0-alpha.1-setup.exe` (and optionally `-win64.zip`)
7. Publish

GitHub will show this with an "Pre-release" badge so it doesn't appear as the "Latest" release.

---

## 10. After distribution — track feedback

Open a GitHub issue label `alpha-feedback` and triage incoming reports into:
- **Blocker for beta** → fix before bumping to 1.0.0-beta.1
- **Minor defect** → post-alpha
- **Enhancement request** → post-1.0.0 (2.x or later)

When it's time to fix the next round, bump `APP_VERSION` to `1.0.0-alpha.2` and tag `v1.0.0-alpha.2`. See the versioning guidance at the top of `src/app/resources/app_info.py`.

---

## Follow-on work already queued

See `docs/POST_ALPHA_TODOS.md` for deferred improvements identified during alpha development. Address those between the alpha and beta releases.

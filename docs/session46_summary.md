# Session 46: Color-Button GSettings Fix + Silica-Fume Stall Diagnosis + Kinetic Save-Bug Fix

**Date:** May 11–12, 2026
**Platform:** macOS (Darwin 25.5.0, arm64)

## Overview

Two unrelated issues debugged in the same session, both arising while the user was actively running scientific simulations on alpha-2.

1. **3D-viewer color-button silent crash** (~1 hour) — clicking a phase color in the Results-page 3D viewer's Phase Controls box silently killed the dev-mode app. Root-caused to a GLib fatal abort in the GTK color-chooser dialog, triggered by missing GSettings schemas. Dev-mode-only; bundled `.app` unaffected. Fixed in `src/main.py`.

2. **Cement + silica-fume hydration stuck at cycle 11** (most of the session) — `HY-ccr152-sf15-ws45-01` ran for 5 minutes, then froze with 100% CPU and no log progress. Root-caused to GEMS-Portlandite oscillation interacting with the kinetics-constraint dt clipping. The fix, found after eliminating two false leads (suppression of sulfate phases; aggressive silica fume kinetics), is to set Portlandite to `Thermodynamic` (no kinetic_data block). That uncovered a second bug: the Hydration panel's kinetic editor dialog does not persist the user's choice to disk, so a UI restart silently resets it. Both bugs fixed in source; the source-code fix is in the working tree pending the user's validation in their next session.

## 3D-Viewer Color-Button Crash

**Symptom.** Clicking the color button next to any phase in the 3D viewer's Phase Controls panel caused the app to vanish with no error dialog. No Python traceback in `thames-crash.log` (a real puzzle initially — `faulthandler` is supposed to catch native crashes, and Session 44 wired it up specifically for this kind of case).

**Diagnosis.** macOS's own crash report (`~/Library/Logs/DiagnosticReports/Python-2026-05-11-111030.ips`) was the key. Faulting thread = main thread, signal = `SIGTRAP` via `g_log_abort`, call chain:

```
g_log_abort  →  g_log_default_handler  →  g_logv  →  g_log  →
g_settings_set_property  →  object_set_property  →  g_settings_new  →
gtk_color_chooser_widget_init  →  gtk_color_chooser_dialog_init
```

GLib aborts when `g_settings_new('org.gtk.Settings.ColorChooser')` can't find a compiled schema. faulthandler can't intercept SIGTRAP issued via GLib's intentional fatal-error path — the only forensic trail is the macOS crash report.

**Root cause.** Ghostty terminal sets `XDG_DATA_DIRS` to `/usr/local/share:/usr/share:/Applications/Ghostty.app/Contents/Resources/ghostty/..`, which does NOT include `/opt/homebrew/share`. When `python src/main.py` is launched from a Ghostty window, GLib can't discover Homebrew's compiled `gschemas.compiled`. `gsettings list-schemas` returns "No schemas installed". The bundled `.app` is unaffected because PyInstaller's `pyi_rth_glib.py` runtime hook sets `GSETTINGS_SCHEMA_DIR` to the bundle's own copy at `Contents/Resources/share/glib-2.0/schemas`.

**Fix** (`src/main.py`, before any GI import): in dev mode on macOS, if `GSETTINGS_SCHEMA_DIR` isn't already set, point it at `/opt/homebrew/share/glib-2.0/schemas` provided the compiled cache file exists. No-op in bundled mode (`getattr(sys, 'frozen', False)` is True there, and PyInstaller's runtime hook handles it). Verified by re-launching dev mode and clicking color buttons in the Phase Controls panel — color picker opens normally.

Committed as `94d9b89d` ("Dev-mode: point GSETTINGS_SCHEMA_DIR at Homebrew on macOS"). Because this is a dev-mode-only fix and alpha-2 testers cannot hit it, the alpha-2 GitHub release was NOT reissued.

## Cement + Silica-Fume Hydration Stall

Most of the session went into this. The user kicked off `HY-ccr152-sf15-ws45-01` (ccr152 Portland cement + 15% silica fume, w/b 0.45, 200³ microstructure, 28-day target). The run advanced through cycles 1-10 with normal dt growth (0.001 → 0.0066 h), then locked up on cycle 11.

### Initial diagnostic snapshot

After 5 minutes wall time:
- `progress.json` last updated at run start (UI tracks progress only at cycle boundaries; this isn't authoritative)
- `thames.log` last modified ~2 min ago, frozen at 185 KB / 1691 lines, cycle 11 the highest cycle reached
- Process at 100% CPU and 9.5 GB RSS — alive and churning, just not advancing simulated time
- dt clipped to 0.0072 h, but `currTime` advanced only 1e-5 h from cycle 10 to cycle 11 (a ~99.9% rollback)
- Arcanite (K₂SO₄) exhausted at cycle 9-10 (1606 voxels → 0); every cycle thereafter triggered `reset DCLowerLimits` + `recall GEM`
- Portlandite asked to GROW by 1,786,978 voxels (17× its current 104k mass) in a single proposed step; CSHQ asked to fully DISSOLVE (55k voxels) at the same cycle; ettringite ditto
- `checkICMoles: IC Ca depleted to -0.502 mol` — IC-recovery injecting 0.5 mol of synthetic Ca and 1.0 mol of OH⁻ per offending cycle (20 such events in 4 minutes vs. 9 in the 1031-cycle sf-free run)

### Comparison against a healthy run

The user pointed out that `HY-ccr152-ws45` (same cement, no silica fume) ran cleanly to cycle 1031, dt reached 0.616 h, only 9 IC-recovery events over the whole run, all of them trivial Cl/Nit-going-to-zero injections of 1e-5 mol. Side-by-side comparison made the variable obvious: silica fume.

### Diagnostic-experimental sequence

Three hypotheses tested by directly editing `simparams.json` in the operation directory and relaunching the C++ binary with `bin/thames -o Result < input.in` (bypassing the UI entirely so we could iterate fast). After each test, the run got the same cycle-11 lockup — `thames.log` would stall mid-cycle-11 lattice operation.

| Attempt | Change | Cycle reached | Ca depletions | Portlandite swing | Status |
|---|---|---|---|---|---|
| 1 (original) | none | 11 (5 min) | 20 | +1.79M voxels | stalled |
| 2 | Sfume rate 4e-8 → 3.3e-9 (user's empirical floor) | 11 (4 min) | 4 | +2.03M | stalled |
| 3 | + straetlingite, syngenite unsuppressed (alternative Ca-Al sinks) | 11 (6 min) | 4 | +2.21M | stalled |
| 4 | Portlandite kinetics → Thermodynamic (delete kinetic_data block) | **19 (7 min)** | **0** | smooth monotonic +2-3k/step | **CLEARED** |

The key data point in attempt 3: straetlingite and syngenite showed ZERO appearances in `thames.log`'s lattice change output. GEMS didn't pick them as Ca-Al sinks. The thermodynamic landscape simply doesn't favor them at this composition. Unsuppressing wasn't enough — GEMS has to *want* the phase.

The Thermodynamic fix in attempt 4 worked because of the kinetics-constraint mechanics. Portlandite-as-Standard puts Portlandite into the `maxRelativeChange=5%` constraint denominator: when GEMS proposes a 17× growth, the constraint clips dt to `0.05 / 16 ≈ 0.3% × requested_dt = 1e-5 h`. The constraint is doing its job — refusing to take an unphysical step — but GEMS keeps proposing the same impossible step on each recall, so the dt stays clipped forever. Portlandite-as-Thermodynamic removes Portlandite from the constraint denominator entirely, letting GEMS settle into its equilibrium solid budget in one big lattice update. After that, the system stays in a stable basin and the kinetics constraint can govern dt growth from the *remaining* primary phases (Alite, Belite, Aluminate, Ferrite).

### Why the working sf-free run didn't hit this

Without silica fume, the GEMS phase landscape near this composition has only one stable solid distribution at every age. No degeneracy → no oscillation → Portlandite grows smoothly (754 → 1837 → 4292 → ... over 8 cycles) and the kinetics constraint is happy. Adding silica fume creates two near-degenerate distributions (different Ca/Si ratios in C-S-H, different ettringite/AFm balance) that GEMS flips between on each recall.

### Result

Run 4 reached cycle 19 in 7 min 35 s with no IC depletion events and dt growing geometrically (×1.5/cycle): 0.0072 → 0.012 h. Loop stopped at the user's "past cycle 15+ with growing dt" success criterion.

The run continued running unattended into overnight. At some point overnight (between yesterday's last check and this morning), the C++ process aborted with SIGABRT (exit 134). The user cleaned up the operation directory before this morning's session, so no logs survive for post-mortem. The Portlandite=Thermodynamic fix is **validated for breaking the cycle-11 cliff**; whether the simulation can run to its 28-day target end with this fix alone is **unknown**. That validation is for the next session.

## Kinetic-Editor Save Bug (discovered during the above debugging)

When the user, looking for the next thing to try, reported that the kinetic editor dialog showed Portlandite as `Thermodynamic` — even though the run's `hydration_config.json` had recorded Portlandite as `Standard` with full rate constants — investigation revealed an architectural asymmetry between two parallel kinetic-editor entry points:

- **Preferences dialog** (`src/app/windows/dialogs/preferences_dialog.py:545`): calls `prefs_service.set_user_default(phase_name, {'type': 'Thermodynamic'})` → persists to `~/Library/Application Support/THAMES/preferences/kinetic_defaults.json`. Survives UI restarts.
- **Hydration panel kinetic dialog** (`src/app/windows/panels/thames_hydration_panel.py::_on_configure_kinetics`): calls `self.product_selector.remove_kinetic_configuration(gems_name)` which sets `kinetic_configurations[gems_name] = {"type": "Thermodynamic"}` in the in-session widget state. **Never persists to disk.** A UI restart (we did two yesterday — the suppression-toggle patches, then the harfbuzz patch) resets the in-session dict from built-in `kinetic_defaults` (which doesn't consult user prefs unless the prefs file has the entry — which it didn't, because nothing in the Hydration-panel path ever writes there). On next Run, `kinetic_configurations[Portlandite]` was Standard defaults, so the saved `hydration_config.json` had Standard.

That's why the user's "I set Thermodynamic in the dialog, the dialog now shows Thermodynamic, but the saved config has Standard" was a real bug, not a workflow confusion.

**Fix** (`thames_hydration_panel.py::_on_configure_kinetics`): now calls `get_kinetic_preferences_service().set_user_default(gems_name, kinetics_or_thermodynamic_marker)` on BOTH the Thermodynamic and non-Thermodynamic OK branches, matching the Preferences-dialog behavior. The two editors now have identical persistence semantics. A second small bug fix in `microstructure_phases_editor.py::_edit_phase_kinetics` corrects an `if new_params:` check that silently dropped `None` (Thermodynamic) returns — defensive fix; this widget isn't currently reachable from any active UI path but the bug was real.

**Validation status:** working-tree only, NOT validated end-to-end. The user must restart the THAMES UI, open the Portlandite kinetic dialog, select Thermodynamic, click OK, and verify `kinetic_defaults.json` gains a `"Portlandite": {"type": "Thermodynamic"}` entry. Validation is on the next-session list.

## POST_ALPHA_TODOS entries added

Five new entries logged in `docs/POST_ALPHA_TODOS.md`:

1. **Load-from-Previous: microstructure-resident phases missing from hydration product tree** — when loading from a prior op's `_hydration_config.json`, the tree starts at C-S-H instead of including the Alite/Belite/Aluminate/etc. that are in the .img.
2. **Load-from-Previous: microstructure field not populated, "no microstructure specified" on run** — after Load-from-Previous, the microstructure file path widget is empty even though the path was recorded in the saved config.
3. **Suppression toggle for microstructure-resident phases: replace silent allow with confirmation dialog** — yesterday's UI patches (since reverted) enabled checkbox toggling of micro-phase rows but the toggle didn't actually propagate to the simparams suppress list. The real fix is a confirmation dialog with explanatory text and proper data-flow plumbing.
4. **Kinetic editor: "Thermodynamic" selection silently discarded when phase already has kinetic parameters** — the symptom that motivated today's fix. Marked as "Being addressed in-session" with the actual code fix described.
5. **Known stall pattern: GEMS-Portlandite oscillation in cement+silica-fume systems** — comprehensive entry on the diagnostic pattern, root cause, and proposed fix (the materials-DB default for Portlandite should be Thermodynamic; backend could also detect the alternating-sign mole-change pattern and act).

## UI patches made and reverted

Earlier today, while still working under the misdiagnosis that the actual fix was to suppress Arcanite + Thenardite, the suppression-toggle UI guards in `hydration_product_selector.py` were patched in two places (`_checkbox_cell_data_func` and `_on_product_toggled`) to allow toggling of microstructure-resident phases. Once we discovered that the toggle didn't actually propagate to `simparams_service`'s suppressed_phases list (because the data model has a separate `microstructure_phases` set that the toggle handler doesn't update), and once we further discovered that the actual fix was Portlandite=Thermodynamic anyway, both patches were reverted via `git checkout`. The findings about the architectural gap are logged in POST_ALPHA_TODOS for a proper future fix.

## Files Modified (committed)

- `src/main.py` — dev-mode GSETTINGS_SCHEMA_DIR fix (already committed as `94d9b89d` yesterday).

## Files Modified (working tree, pending validation)

- `src/app/widgets/microstructure_phases_editor.py` — `_edit_phase_kinetics` None-handling fix.
- `src/app/windows/panels/thames_hydration_panel.py` — `_on_configure_kinetics` now persists kinetic choice to user prefs.
- `docs/POST_ALPHA_TODOS.md` — 5 new entries.
- `docs/session46_summary.md` — this file.
- `CLAUDE.md` — Session 46 entry.

## Files Modified (NOT committed)

- `.claude/settings.local.json` — local Bash permissions accumulated during testing.
- `config/preferences.yml` — window position only.
- `.claude/scheduled_tasks.lock` — transient ScheduleWakeup lock.

## Verification

- `94d9b89d` (color-button GSettings fix) verified live in dev mode by the user (color picker opens normally).
- Cement + silica-fume cycle-11 stall verified cleared by switching Portlandite to Thermodynamic (cycle 19 reached cleanly with healthy dt growth and zero IC depletion events).
- Kinetic save-bug fix NOT yet verified end-to-end. Pending next-session validation by user: set Thermodynamic via UI → restart THAMES → confirm choice persists in `kinetic_defaults.json` → run with persisted choice.
- The Sfume-rate change to 3.3e-9, while consistent with the user's measured silica-fume dissolution rates, was not, on its own, sufficient to fix the stall. May or may not be worth keeping as a materials-DB default; deferred.
- Long-term run with Portlandite=Thermodynamic to its 28-day target: NOT yet verified. The overnight run aborted with SIGABRT after some hours; no logs survived for post-mortem.

## Open questions for next session

1. **End-to-end validation of the kinetic save-bug fix** — restart UI, exercise the kinetic dialog, confirm `kinetic_defaults.json` updates.
2. **End-to-end run of HY-ccr152-sf15-ws45 with Portlandite=Thermodynamic** — does the simulation reach its 28-day target without a later-age failure?
3. **What caused the overnight SIGABRT?** If reproducible, capture `thames.log` and `~/Library/Logs/DiagnosticReports/Python-*.ips` before it gets cleaned up.

## Cumulative file changes for Session 46

Committed (yesterday): `src/main.py` (one-line dev-mode env fix).
Pending commit (today's wrap-up): `src/app/widgets/microstructure_phases_editor.py`, `src/app/windows/panels/thames_hydration_panel.py`, `docs/POST_ALPHA_TODOS.md`, `docs/session46_summary.md`, `CLAUDE.md`.
Reverted via `git checkout` during the session: `src/app/widgets/hydration_product_selector.py` (suppression-toggle UI patches that were the wrong fix).

# Session 63 — 2026-08-25

**Focus.** macOS verification of the S61+S62 Windows-hotfix fix bundle. Discovered dead migration wire-up and fixed it. Decided against a Mac alpha-2.1 hotfix; deferred to alpha-3.

**Commit.** `fbb87b60` — Session 63: wire MigrationManager into ServiceContainer startup.

**Nothing pushed at time of wrap-up.**

---

## Where we started

- Fresh mac session after two Windows sessions (S61, S62) I did not attend.
- Two catch-up memories authored by Jeff: `project_alpha2_macos_followup.md`, `project_nist_patch_state.md`.
- `main` behind origin by 8 commits + submodule bump. Synced via individual `pre-session-sync.sh` steps (script-as-a-whole rejected — remembered per Jeff's preference).
- Ended sync: super-repo `238389b5`, submodule `6f40f4a`.

## Verification plan

Six items in the fix bundle. Only three needed dynamic verification on Mac:

| # | Fix | Mac state after read-only trace |
|---|---|---|
| 1 | `fbf392b` ws2_32 link | N/A (BSD sockets in macOS libc) |
| 2 | `60f8de26` micgen triple-fix (double-free NULLs, particle pointer-array bounds, fclose ordering) | latent on Mac; needs run |
| 3 | `7a9ba095` glass-phase migration `20260824_01_glass_phase_am_rename` | needed DB inspection |
| 4 | `6f40f4a` DC-depletion clamp + `runmeta::finalize` on `scaledMass<0` | applies to Mac too; needs rebuild + run |
| 5 | `13511a55` pointer bump | trivial |
| 6 | `f21c773d` zero-content correlation skip + `rand3d fabs(sdiff)<1e-12` guard | latent on Mac; needs run with cement151 |

Test target: `cem151-fa-1` microstructure → `HY-cem151-fa1-1` hydration (28 d). cem151 has 0.0% K2O → exercises the zero-BLOB skip. ClassF-FlyAsh has bare glass names → exercises the migration. Fly-ash 28-day run exercises the DC-depletion clamp.

## What happened, in order

### Step 1 — static reads

All four fix regions confirmed present in current source:

- `KineticController.cc:2114-2135` — depletion clamp (was `exit(0)`).
- `KineticController.cc:2144-2165` — `runmeta::finalize(1, "...: scaledMass < 0", diag)` before `exit(1)`.
- `micgen.c:6584` — `if (fabs(sdiff) < 1.0e-12) { fprintf(...); return 4; }`.
- `micgen.c:512-515, 1033` — pointer NULLs after intermediate frees.
- `migrations.py:270` — `_apply_glass_phase_am_rename_migration()` with the five UPDATE statements.
- `migrations.py:500-502` — check + call inside `upgrade_database()`.
- `micgen_input_service.py:42` — `_correlation_blob_is_degenerate` module-level helper.

### Step 2 — DB migration state

```sql
SELECT gem_phase_name, COUNT(*) FROM material_phase
WHERE gem_phase_name IN ('C2AS','CA2S',...,'K6A2S(am)') GROUP BY gem_phase_name;
```

Result: `CA2S|1`, `CAS2|1`. Bare glass names still present, no `(am)`-suffixed rows. Migration had NOT run.

Applied migrations table: latest was `20250906_001` (Sep 2025) — the S61 migration was absent.

Log grep on `thames.log` for `migrat|glass|upgrade_database`: **zero hits.** Migration never fired during any UI launch.

### Diagnosis of the dead wire-up

```
$ grep -rn 'MigrationManager()\|.upgrade_database\|create_migration_manager' src/ | grep -v migrations.py
src/app/database/__init__.py:11:from app.database.migrations import MigrationManager, Migration, create_migration_manager
src/app/database/__init__.py:26:    'create_migration_manager'
```

Two references, both in `__init__.py` re-exports. **No live caller anywhere in the app.**

`ServiceContainer.__init__` stored `self.db_service` but never invoked the migration manager. `DatabaseService.initialize_database()` called `create_all_tables()` + `_initialize_default_data()` — no migration pass.

Historical evidence: the DB carried `002_add_mix_design_table` (Aug 2025) and `20250906_001` (Sep 2025), so some caller **used** to exist and was later removed without noticing. Neither commit that added those migrations is visible in the git log for the current `migrations.py` file. Origin lost.

**Why S62 Windows verification worked despite this:** Jeff's Windows box likely did a fresh install of alpha-2.1 (installer wrote the post-S59 seed DB with `(am)` names already), or Jeff manually applied the SQL earlier. Neither would apply to a NIST tester who upgraded in place (installer preserves user data). **The Windows hotfix has a latent gap: any in-place-upgrade tester still has bare glass names.**

### Step 3 — rebuild

```
rm -f bin/thames bin/micgen
./build-macos.sh
```

Rebuild clean. New binaries at 14:39.

### Track 1 (mac DB unblocking SQL)

```sql
BEGIN;
UPDATE material_phase SET gem_phase_name = 'C2AS(am)'  WHERE gem_phase_name = 'C2AS';
UPDATE material_phase SET gem_phase_name = 'CA2S(am)'  WHERE gem_phase_name = 'CA2S';
UPDATE material_phase SET gem_phase_name = 'CAS(am)'   WHERE gem_phase_name = 'CAS';
UPDATE material_phase SET gem_phase_name = 'CAS2(am)'  WHERE gem_phase_name = 'CAS2';
UPDATE material_phase SET gem_phase_name = 'K6A2S(am)' WHERE gem_phase_name = 'K6A2S';
INSERT INTO migrations (version, name, applied_at, created_at, updated_at)
VALUES ('20260824_01_glass_phase_am_rename', 'Rename bare glass phases to (am) form ...',
        datetime('now'), datetime('now'), datetime('now'));
COMMIT;
```

Applied cleanly. Post-check: `CA2S(am)|1`, `CAS2(am)|1`, no bare rows. Migration row recorded. Unblocked steps 4/5.

### Track 2 (permanent wire-up fix)

Added to `src/app/services/service_container.py::ServiceContainer.__init__` immediately after `self.database_service = self.db_service`:

```python
try:
    from app.database.migrations import create_migration_manager
    migration_manager = create_migration_manager(self.db_service)
    migration_manager.upgrade_database()
except Exception as e:
    self.logger.error(f"Migration upgrade failed at startup: {e}")
```

Design notes:
- **Idempotent.** Applied migrations are skipped inside `upgrade_database()`.
- **Doesn't re-raise.** A migration failure logs an error and keeps the app launchable — data-integrity issues surface downstream where the user can act on them.
- **Runs exactly once per process.** ServiceContainer is a singleton with idempotent `__init__` (guarded by `hasattr(self, '_initialized')`).
- **No circular-import risk.** Import is inside the try-block, deferred to first ServiceContainer instantiation.

Verified from a fresh Python interpreter:

```
$ python -c "from app.services.service_container import ServiceContainer; ServiceContainer()"
VCCTL.Database - INFO - Database service initialized with: sqlite:////...thames.db
VCCTL.Database - INFO - Default database data initialized successfully
VCCTL.Database - INFO - Database initialized successfully
VCCTL.Migrations - INFO - Database already initialized
VCCTL.Migrations - INFO - Current version: 20260824_01_glass_phase_am_rename
VCCTL.Migrations - INFO - Applied migrations: ['001', 'seed_001', 'flyway_migration_001',
                                               '002_add_mix_design_table', '20250906_001',
                                               '20260824_01_glass_phase_am_rename']
VCCTL.ServiceContainer - INFO - Service container initialized
```

Six-migration enumeration reaches the log; glass entry recognized as already applied (Track 1's manual insert). Cross-platform: pure Python init, no platform guards.

### Step 4 — micgen for cem151-fa-1

Jeff drove the UI. Operation folder `cem151-fa-1` contained:

- `cement151.alu`, `.c3a`, `.c3s`, `.c4af`, `.sil` — all 713 B (nonzero correlations)
- **`cement151.k2o` ABSENT** — zero-BLOB skip fired
- `.thames.img` (253 KB), `.thames.pimg` (293 KB) written correctly
- `micgen_progress.json` present, step Complete

Log line at 15:30:22 (verbatim S62 message):

> `Correlation function 'k2o' for clinker 'cement151' is degenerate (all values near zero); treating as absent and skipping write. Micgen will skip this phase via its missing-file handler.`

**Fix 6 verified.** No micgen crash → **Fix 2 verified.**

### Step 5 — hydration HY-cem151-fa1-1 (672 h)

Provenance sidecar (`Result/run_metadata.json`):

- `git_hash: 6f40f4ac` ✓ (matches freshly-synced submodule)
- `build_date: 2026-08-25T19:39:07Z` ✓ (matches today's 14:39 rebuild)
- `compiler_id: AppleClang 21.0.0.21000101` ✓
- `cxx_flags: -O2 -std=c++17 -DIPMGEMPLUGIN -Wall ...` ✓
- `platform: {system: Darwin, machine: arm64, ...}` ✓
- `gems_dch.sha256: afd4cf8a...` ✓ (C3S/C3A/glass-corrected DCH)
- `thames_ui.version: 1.0.0-alpha.2.1`, `python_version: 3.14.7` ✓
- `exit_code: 0`, `success: true`, `exit_reason: "Simulation completed successfully"`
- diagnostics: `672 hours in 4589 cycles. AdaptiveTimeController: dt=4.000e+00h, total=4589 (4589 ok, 0 fail), success_rate=100.0%`

Clamp warning count in log: **216.** All handled; zero aborts. **Fix 4 verified.**

Comparison against S62 Windows cem151-fa-1:

| Metric | Windows | Mac today |
|---|---|---|
| Simulated | 672 h | 672 h |
| Cycles | 2363 | 4589 |
| Wall clock | 3.6 min | 2.0 min |
| DC-depletion clamps | 71 | 216 |
| Exit code | 0 | 0 |
| Adaptive success rate | 100% | 100% |

Cycle count 2× higher on Mac. Double-precision arithmetic ordering differences (FMA behavior, math libs) → adaptive stepper takes smaller steps at some cycles. Both end at dt=4.0 h max with 100% success rate. Not a regression.

## Decisions taken

### Mac alpha-2.1 hotfix: NO. Defer to alpha-3.

Analysis: distributed `THAMES-1.0.0-alpha.2-macOS.zip` (S45, May 2026) is 5 months stale. Six bugs latent in it:

- Long fly-ash runs abort mid-simulation (S62 clamp) — severe
- cement151 SIGSEGV during microstructure gen (S62 rand3d) — severe
- ClassF-FlyAsh Bug A (S59) — severe (partly masked because S45 seed DB has matching bare names)
- Mix Design 32³ silent failure (S47) — moderate
- Silica-fume cycle-11 oscillation (S55) — moderate
- Kinetic-editor save silently no-op (S46) — moderate

Jeff confirmed **no known Mac tester currently on alpha-2.** Alpha-3 will bundle all of S46-S63 across both platforms.

### NIST tester wire-up notification: WAIT for report

If NIST tester took the installer path and upgraded in place, they may have latent bare glass names in their DB. `upgrade_database()` was never fired for them either. If they hit Bug A on ClassF-FlyAsh, respond with the manual SQL snippet (Track 1 form) — smallest surface, no repackage needed. Otherwise the fix silently reaches them via alpha-3.

## POST_ALPHA additions

- **Startup migration wire-up: no test guards the "does upgrade_database() actually get called?" invariant** (LANDED point fix, class of bug open until smoke test or registry refactor lands). Proposes (a) a startup smoke test on an empty temp DB, or (b) the registry-driven migration loop from S61's phase-rename POST_ALPHA. Cross-references that LANDED item.

## Files touched this session

- `src/app/services/service_container.py` — wire-up (Track 2)
- `docs/POST_ALPHA_TODOS.md` — class-of-bug entry
- `docs/session63_summary.md` — this file
- `CLAUDE.md` — S60-63 compressed history
- `bin/thames`, `bin/micgen`, `bin/libpng16.16.dylib` — rebuilt from freshly-synced submodule
- `~/Library/Application Support/THAMES/database/thames.db` — Track 1 manual SQL
- Persistent memory: `project_nist_patch_state.md` and `project_alpha2_macos_followup.md` updated with S63 addenda.

## Handoff to next session

- `fbb87b60` on `main` is unpushed at time of writing.
- Next physics session can execute `docs/CNT_DIAGNOSTIC_PLAN.md` (portlandite zero-placement) whenever Jeff wants to return to it.
- Alpha-3 planning: needs a proper release-notes draft covering S46-S63. Two-platform build. Windows install already at `1.0.0-alpha.2.1`; version bump narrative to figure out.
- Windows glass-phase auto-inject investigation (S59 residual) still open.

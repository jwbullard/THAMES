# Session 59 Summary — 2026-08-22

Three ship-blocker-adjacent fixes landed for the NIST alpha-3 push, plus infrastructure notes for future sessions.

## Order of work

1. Bug B (portable filesystem) drafted in S58 — applied.
2. Glass-phase Bug A investigation and permanent fix via DCH rename.
3. Electrolyte-fixed bias fix (S57-diagnosed) — landed.
4. Post-work docs, memories, wrap-up.

## Bug B: portable filesystem — LANDED

Draft from S58 scratchpad applied. Replaced 9 shell-out sites in `backend/thames-hydration/src/thames.cc` (2× `mv -f`, 6× `cp -f`, 1× `mkdir -p`) with `std::filesystem` helpers (`moveFileInto`, `copyFileInto`, `ensureDir`) that preserve the existing `FileException` error path. `#include <filesystem>` added to `thames.h`. Cross-platform because C++17 is already enabled and modern libc++/libstdc++/MSVC ship `<filesystem>` in the default runtime — no separate `-lstdc++fs` linker flag needed.

**Also cleaned up dead code** in `deleteDynAllocMem` — the `string buff = ""` and `int resCallSystem;` locals are no longer used after the shell-outs are gone. Removed per Jeff's "prefer delete over dead code" principle (see [[feedback_dead_code_delete]]).

**Verified end-to-end on macOS.** Ca11mM smoke fixture runs to `exit_code: 0, exit_reason: "Simulation completed successfully"` in 27 s — `ensureDir` created `Result/` cleanly, `copyFileInto` produced all 6 input files (dch/ipm/dbr/dat.lst/img/simparams), `moveFileInto` moved `ipmlog.txt` (the `if (f.good())` guard correctly skipped `IPM_dump.txt` when GEMS didn't emit one). No behavior change on macOS. Windows validation requires access to the Windows box.

Not yet actually tested on Windows. That's the residual verification for this fix.

## Glass-phase Bug A — LANDED via DCH rename

### Diagnosis

The 5 glass phases (`C2AS`, `CA2S`, `CAS`, `CAS2`, `K6A2S`) used bare names in the GEMS data files (DCH, DBR, `material_phase` DB) but `(am)`-suffixed names in the UI (SUGGESTED_PRODUCTS, kinetic_defaults, elastic_defaults, phase_color, pozzolan_names). S37 had added `(am)` to the UI dicts but never propagated to the DCH.

The failure mechanism: when `hydration_products` contained an `(am)`-suffixed key, `PhaseDataBuilder.build_gemphase_data("C2AS(am)")` called `gems_parser.get_phase("C2AS(am)")` against a DCH that only knew `C2AS` (bare) → returned None → `simparams.json` entry lacked `gemphase_data` → backend `parseMicroPhases` threw `DataException: "Microstructure phase C2AS is not Void but has no GEM pahse data?"`.

**Reproduced directly.** `python3 -c "from app.services.gems_parser_service import GEMSParserService; p=GEMSParserService('src/data/gems'); [print(f'{n} -> {p.get_phase(n)}') for n in ['C2AS','C2AS(am)']]"` yielded bare FOUND, `(am)` None.

Bug A wasn't Windows-specific. Windows-only was just the *trigger* — the UI on Windows auto-adds glass phases to `hydration_products` even when the microstructure doesn't contain them. On macOS the same crash would happen if a user manually ticked a glass phase.

### Discussion about the fix direction

Two candidate paths:
- **Path A (UI-side)**: roll back S37 — remove `(am)` from all UI service dicts.
- **Path B (DCH-side)**: add `(am)` to the DCH so it matches the UI.

I originally recommended Path A on the argument that the DCH is a downstream artifact of CemData18 and forking it silently is bad. Jeff pushed back with the key context: he already maintains a private fork of CemData18 (he added several phases including `C2AS`, `CAS2` originally to build the augmented DCH THAMES uses). So the "don't fork CemData18" concern was moot. The right approach was to make the DCH match the UI's convention rather than paper over with UI-side normalization kludges. Jeff's exact framing: "it's much more important to avoid kludges in the UI or backend C++ code where we check parts of name strings to make up for inconsistencies in the underlying data files."

### Full rename scope (all landed together)

- `src/data/gems/thames-dch.dat` — PHNL + DCNL renamed (20 substitutions total, 5 phases × 2 refs × 2 sections). Backup at `thames-dch.dat.pre-glass-am-rename-20260822`.
- `src/data/gems/thames-dbr.dat` — 10 substitutions. Backup `thames-dbr.dat.pre-glass-am-rename-20260822`.
- `src/data/gems/thames-ipm.dat` — no changes needed (didn't reference these names).
- `src/data/database/thames.db` — 2 rows in `material_phase` for ClassF-FlyAsh (material_id=48: `CA2S` → `CA2S(am)`, `CAS2` → `CAS2(am)`). Backup `thames.db.pre-glass-am-rename-20260822`. `CAS`, `C2AS`, `K6A2S` weren't present.
- `src/app/services/simparams_service.py` — deleted the 5 `(am)`-to-bare entries from `_get_thamesname` name_mappings dict. That mapping was actively stripping `(am)` from the display name at the boundary; without deletion the DCH rename would be defeated.
- `backend/thames-hydration/src/thameslib/ChemicalSystem.cc` — hardcoded `colorN_["C2AS"]` / `colorN_["CA2S"]` / `colorN_["K6A2S"]` initializer blocks renamed to `(am)` form (6 hits each, 18 substitutions). Matching commented-out `elasticModuli_["..."]` block also renamed for consistency (5 hits each, 15 more substitutions).

### User-side artifacts

Two local microstructures (`~/Library/Application Support/THAMES/operations/OPC-FA-30`, `HY-OPC-FA-30`) had bare glass names in `_phase_mapping.json` and were moved to `scratchpad/pre-am-rename-ops/` — would silently break on re-hydration. Jeff can regenerate on demand.

### Verified end-to-end

1. Python parser: 5 phases resolvable at `(am)` names, bare returns None (correct). Phase count 100, DC count 197 — identical to pre-rename.
2. `PhaseDataBuilder.build_phase_entry("C2AS(am)")` now produces a valid entry with populated `gemphase_data` — the direct Python-side cause of Bug A is gone at the source. Ran for all 5 phases; clean.
3. Clean rebuild.
4. Ca11mM smoke fixture: 27 s, exit 0.
5. CSV byte-parity: 26/29 identical; 3 differ only in glass-phase column-header names (bare → `(am)`). Zero simulation-data regression.
6. Backend `getGEMPhaseId("C2AS(am)")` succeeds. Proved by contradiction — the first smoke-test attempt (before I updated the fixture's `suppressed_phases` from bare) failed with `Could not find GEMPhaseIdLookup_ match to C2AS`, confirming the DCH's `GEMPhaseIdLookup_` is populated correctly.

### Windows glass-phase auto-inject: downgraded, not gone

Bug A crash is closed. But the **underlying Windows-only bug** — the UI auto-adding glass phases the user didn't select — remains. Post-Fix-A, it's downgraded from a hard ship-blocker (crash) to a cross-platform reproducibility bug (Windows simparams.json ≠ macOS simparams.json for identical UI inputs; different phase-ID assignments across platforms; different `suppressed_phases` lists). GEMS wouldn't precipitate a glass phase in a Portland pore solution because SI(glass) is very low, so user-visible physics differences are unlikely but not proven zero. **Still needs fixing before beta or before any cross-platform validation study.** Investigation deferred to next Windows-access session.

I originally called it "cosmetic-only" and Jeff correctly pushed back that this was overselling. The corrected characterization is above.

### POST_ALPHA filed

"Eliminate hardcoded phase-name strings in ChemicalSystem.cc" — the `colorN_` / `elasticModuli_` initializer blocks are the deeper class of fragility that made this fix necessary. Roughly 500 lines of C++ initializer to move into a shared JSON data file with a startup validation pass. Full entry in `docs/POST_ALPHA_TODOS.md`.

## Fix C: electrolyte-fixed bias — LANDED

Symmetric IC transfer applied to `ChemicalSystem::setElectrolyteComposition`. The `if (deltaDCMoles > 0)` gate at line 4431 is removed; both directions of transfer now work.

### Validation

Against the S57 Garrault fixtures at `~/tmp/thames-alite-Ca11mM` and `~/tmp/thames-alite-Ca22mM`:

| | Pre-fix (S57 reported + reproduced today) | Post-fix (today) |
|---|---|---|
| Ca11mM total Ca | 12.05 mM (10% high) | 11.58 mM (5% high) — bias halved |
| Ca11mM peak total Si | 85.5 μM | 104.6 μM — physical: lower Ca → higher CSHQ-eq [Si] |
| Ca22mM total Ca | 23.55 mM (7% high) | 23.22 mM (5.5% high) — bias reduced |
| Ca22mM peak total Si | 31.9 μM | 32.2 μM — unchanged |

### Belt-and-suspenders DC-bounds pinning tried and REVERTED

Attempted `DCLowerLimit_[DCId] = DCUpperLimit_[DCId] = target ± tol` at ±1e-15, ±1%, ±5%. All three failed:
- ±1e-15: GEMS convergence failure in Ca11mM at cycle 10. Three interdependent pinned Ca species (Ca+2, CaOH+, OH-) over-constrain the K equilibrium.
- ±1%: same failure at cycle 10.
- ±5%: both runs complete but **Alite dissolution collapses to essentially zero** (0.006-0.03% DOR in 1.2 h) because pinning the aqueous Ca+2 blocks the kinetic dissolution products from leaving the aqueous phase — GEMS interprets the bound as "this DC cannot exceed target" and suppresses reactant dissolution to satisfy the constraint.

The correct semantics for `condition: "fixed"` is "external reservoir absorbs/supplies as needed", which the symmetric IC-transfer alone models correctly. GEMS's re-equilibration will drift the DC slightly (~5% in Garrault runs) because it re-partitions among Ca-bearing complexes not covered by the fixed DCs. That drift is within any realistic reservoir precision envelope.

## Personal-lesson diversion: phantom peak-Si "regression"

Spent ~30 min bisecting a nonexistent regression. Post-fix Ca11mM peak SiO2@ + HSiO3- reported as 4.9 μM against S57's reported 85.5 μM peak total-Si. Bisected the submodule all the way back to S57's own `1bdf5d5` — same 4.9 μM. Then realized: I was summing only the free-Si species. Adding CaSiO3@ (72 μM) and MgSiO3@ (7.8 μM) — which S56 CLAUDE.md explicitly warned about — recovered the 85.48 μM peak that matches S57 within noise. Zero physics regression ever existed.

**S56 CLAUDE.md discovery** (compressed but preserved): "at high Ca+Si concentrations most Si goes into the CaSiO3@ ion-pair complex, not free SiO2@ or HSiO3⁻. GEMS accounts for this properly. But 'free silica' concentrations in Solution.csv can be misleading — sum all Si-bearing DCs (AlHSiO3+2, AlSiO5-3, CaSiO3@, MgSiO3@, HSiO3−, SiO2@, SiO3²⁻) for total aqueous Si."

**POST_ALPHA filed** to prevent this class of user error permanently: add derived per-element total columns (`total_Si`, `total_Ca`, etc.) to `Solution.csv`, computed as `Σ DCMoles × getDCStoich(dcId, icId)`. Backend has the stoich table already.

Also written up as a persistent memory: `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/reference_total_si_accounting.md`.

## Ship-blocker status for NIST alpha-3

- Bug A (parseMicroPhases crash on glass-phase configs): **CLOSED** by DCH rename
- Bug B (`cp`/`mv`/`mkdir` shell-outs unrecognized on Windows cmd.exe): **CLOSED** by std::filesystem port
- Bug C (no `exit_status.json` in Result folders): CLOSED in S58 by replacement with `run_metadata.json`
- F1 (runmeta::initialize fires too late for early crashes): CLOSED in S58
- F2 (Running → Pending on backend crash): CLOSED in S58
- Microstructure-restoration on Load Operation: CLOSED in S58

Nothing else blocks the alpha-3 push from a code standpoint. Windows-side smoke testing still recommended before shipping to NIST.

## Pickup list for next session

1. **Windows validation of Bug B + Bug A fixes** — top priority. Confirm that Windows cmd.exe no longer chokes on the file operations and that a fly-ash-containing hydration op completes without crashing. Would ideally also reproduce the Windows-only glass-phase auto-inject to isolate its trigger for the next fix cycle.
2. **Windows glass-phase auto-inject investigation** — see above; downgraded to reproducibility bug but still needs a fix before beta or any cross-platform validation study.
3. **NIST alpha-3 release cut** — assuming Windows validation passes, this session's fixes are the last blocker.
4. **JMAK-CSHQ implementation** — physics backlog carried from S57. The S57 [Si] decay from peak to plateau (Garrault Fig 2 shows 85 → 45 μM at Ca11mM over 5-30 min) isn't captured because CSHQ is Thermodynamic — needs JMAK-per-voxel treatment analogous to JMAK-Portlandite from S54.
5. **Pure-alite portlandite CNT investigation** — physics backlog from S58 addendum. Four candidate failure modes documented in `docs/session58_summary.md`.
6. **C2S / C4AF calibration audits** — physics backlog from S57. Need calibration papers.

## Uncommitted state going into the commit (documented for the wrap-up commit itself to reflect)

- Submodule (`backend/thames-hydration/`): `src/thames.cc`, `src/thames.h`, `src/thameslib/ChemicalSystem.cc`
- Super-repo: `docs/NIST-diagnostic.md`, `docs/POST_ALPHA_TODOS.md`, `docs/session59_summary.md` (this file), `src/app/services/simparams_service.py`, `src/data/database/thames.db`, `src/data/gems/thames-dbr.dat`, `src/data/gems/thames-dch.dat`, plus the submodule pointer bump
- Local config drift: `.claude/settings.local.json`, `config/preferences.yml` — leaving as-is

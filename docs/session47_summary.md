# Session 47 — Mix Design schema-bound silent-failure fix, ThamesRender scoping
June 4, 2026 — macOS

Started as a memory check ("do you have THAMES context loaded?") and a scoping conversation about a new sibling project for publication-quality rendering. Pivoted into a real bug fix when the user reported that creating a 32³ microstructure in the alpha-2 bundled app silently did nothing. Ended with a memory save and the wrap-up.

## ThamesRender — scoping decision

User wants a separate workflow to take THAMES result-folder microstructure data and produce publication-quality 3D perspective images, with an MP4 option for time evolution. The in-app PyVista viewer is fine for interaction but not publication-grade.

Recommended **separate project at `~/Code/ThamesRender/`**, not integration into THAMES. Reasons:
- A publication renderer doesn't need GTK, the database, or the operations system.
- Iteration cycle for rendering quality shouldn't be coupled to an alpha-stage GUI app.
- Can later be wired into THAMES as a post-completion hook (same pattern as Concelas) if integration ever becomes worthwhile.

Main tradeoff: phase color mapping and voxel-ordering conventions live in THAMES, so the new tool either imports them as a package or duplicates ~100 lines. Recommended import.

No implementation work — just the scoping. User will start a fresh Claude Code session in `~/Code/ThamesRender/` next.

## Bug — empty operation folder for `ccr152-ws45-32`

User's `~/Code/THAMES/dist/THAMES.app` (the published alpha-2 bundle from Session 45) created the operation folder at `~/Library/Application Support/THAMES/operations/ccr152-ws45-32` but produced no input files and never launched `micgen`. User suspected dimension validation.

### Investigation

`thames.log` showed three attempts on June 4 at 17:03, 17:05, and 17:10. The 17:10 attempt logged a buried error:

```
THAMES.MixDesignPanel - ERROR - ❌ Error auto-saving mix design: 1 validation error for MixDesignCreate
system_size
  Input should be greater than or equal to 50 [type=greater_than_equal, input_value=32, input_type=int]
```

Followed by:

```
THAMES.MixDesignPanel - ERROR - ❌ CRITICAL: Auto-save returned None - this will break data tracking!
...
THAMES.MixDesignPanel - ERROR - No saved mix design ID - cannot generate input file
```

No error dialog. No toast. From the user's perspective, the click did nothing.

### Root cause

`src/app/models/mix_design.py` had a stale legacy `system_size` bound:

```python
system_size_x: int = Field(ge=25, le=400, default=100)
system_size_y: int = Field(ge=25, le=400, default=100)
system_size_z: int = Field(ge=25, le=400, default=100)
system_size: int = Field(ge=50, le=500, default=100)  # Keep for backward compatibility
```

The Mix Design panel saves both the per-axis fields AND the legacy single-dim `system_size` from the same X spin button. 32 passes per-axis validation (≥25) but fails the legacy field (≥50). Pydantic aborts the whole `MixDesignCreate`, auto-save returns `None`, and `mix_design_panel.py` exits the generation flow.

The empty operation folder is a side-effect of folder-creation ordering: `Created mix folder` happens BEFORE validation, leaving an orphan on every failed attempt.

### Fix

Relaxed the legacy bound to match the per-axis bound:

- `mix_design.py:154`: `system_size: int = Field(ge=25, le=400, ...)` (was `ge=50, le=500`)
- `mix_design.py:255`: same bound in `MixDesignUpdate` Optional.

Verified the patched venv loads the new constraint:

```
system_size metadata: [Ge(ge=25), Le(le=400)]
```

User re-ran the GUI from source (`./thames-env/bin/python src/main.py` from `~/Code/THAMES/`) and the 32³ microstructure generated successfully.

### Important caveat

The fix is in the **source tree only**. The published alpha-2 bundle (`dist/THAMES.app`, plus the Windows .exe / .zip on the GitHub release) still has the `ge=50` bug. Any tester running the published bundle who enters a system size < 50 will hit the same silent failure. Two consequences:

1. POST_ALPHA_TODOS entry for the silent-failure UX issue (the validation error needs to surface as a dialog, not just log).
2. Amendment to the published alpha-2 release notes so testers see the workaround.

## POST_ALPHA_TODOS entry

Drafted "Mix Design auto-save: surface Pydantic ValidationError instead of silently failing" at `docs/POST_ALPHA_TODOS.md`. Notes that:
- The schema bound itself was fixed in-session.
- The deeper UX bug is the silent `try/except` swallowing the ValidationError.
- Proposed fix: branch on `pydantic.ValidationError` and pop a `Gtk.MessageDialog` with the offending field list; create the operation folder AFTER validation succeeds, not before.

## release-notes-alpha-3.md — new working-draft pattern

Created `release-notes-alpha-3.md` at the THAMES repo root. Plain-text format matching the alpha-2 release notes, with four sections: `Fixed since alpha-2 / Added / Changed / Known Limitations`. First entry is the schema-bound fix, with explicit "Workaround on alpha-2: use a system size of 50 or larger" so testers can find the workaround in the next release's notes without backtracking.

The pattern: accumulate fixes here as they land in the source tree, then `gh release create v1.0.0-alpha.3 --notes-file release-notes-alpha-3.md ...` at release time.

## Amended the published v1.0.0-alpha.2 release notes

Used `gh release edit v1.0.0-alpha.2 --notes-file /tmp/thames-alpha2-notes.txt` to add item 7 to Known Limitations:

> Mix Design silently rejects system sizes below 50. Entering an X, Y, or Z system size of 25-49 in the Mix Design panel causes the "Generate" click to do nothing visible … Workaround: use a system size of 50 or larger. Fixed in alpha-3.

Verified the edit took effect at https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.2.

This is a workflow the user previously authorized once; saved as a feedback memory so it generalizes automatically the next time a source-tree fix lands for an already-published bundle bug.

## Memory write

New memory: `feedback_alpha_release_notes_workflow.md`. Rule: when a fix lands in source but the published alpha bundle still has the bug, both update the working-draft `release-notes-alpha-N.md` AND amend the published release's Known Limitations via `gh release edit`. Pointer added to `MEMORY.md`.

Deliberately did NOT save:
- The schema fix specifics (in code + git blame).
- The Pydantic-error debug recipe (covered by the POST_ALPHA_TODOS entry).
- ThamesRender scoping (premature — that project hasn't started; cross-coupling is hypothetical).
- venv path / log paths (already in CLAUDE.md global instructions).

## Files changed

- `src/app/models/mix_design.py` — schema bound fix (two lines).
- `docs/POST_ALPHA_TODOS.md` — new entry for the silent-failure UX issue. (Pre-existing edit in this file from earlier today — the "Lattice-trapped phase blocks GEMS" entry — is also committed in the same session.)
- `release-notes-alpha-3.md` — new working draft at repo root.
- `docs/session47_summary.md` — this file.
- `CLAUDE.md` — Session 47 entry.

## Pending when session resumes

- ThamesRender project scaffolding (new session in `~/Code/ThamesRender/`).
- Decide whether to rebuild the alpha-2 .app and .exe artifacts with the schema fix backported, or leave the published bundle as-is and rely on the amended release-notes workaround until alpha-3.
- The silent-failure UX bug (POST_ALPHA_TODOS entry) — still open; the schema-bound symptom is the most visible instance but the underlying pattern (`try/except` swallowing `ValidationError`) likely exists at other auto-save call sites and is worth a panel-wide audit.

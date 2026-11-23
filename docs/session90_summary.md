# Session 90 (Nov 23, 2026): alpha-4.4 — failed runs shown as Failed, Logs tab, published

Driven by tutorial Ep 9 (When Things Go Wrong): a GEMS failure finished as
"Completed, 100 %". Work list: `docs/UI-Issues.md` → alpha.4.4.

## Commits (all pushed)

| Commit | What |
|---|---|
| submodule `a27385f` | Backend 6.0.1: `runmeta::recordedExitCode()`; `deleteDynAllocMem` exits 1 when a recorded finalize carried a nonzero code. Tagged `v6.0.1` |
| `ff91efbe` | UI: `src/app/utils/run_outcome.py`; execution services and Operations panel use it; Logs tab + Export Logs; issue template; version 1.0.0-alpha.4.4 |
| `15852faa` | `docs/alpha-4.4-windows-build.md` |
| `360ca40a` | (Windows, Jeff) Duration clock stops when a run fails; Windows installer recorded |
| `fde54f52` | `release-notes-alpha-4.4.md`; macOS zip recorded. Release tag `v1.0.0-alpha.4.4` |

## The failure bug

- **Backend:** `Controller.cc:1287` calls `runmeta::finalize(1, "GEMS solver
  exceeded maximum consecutive failures")` and then `break`s; `finalize` is
  first-call-wins, so the sidecar was right but the process exited 0.
- **UI:** hydration runs go through `ThamesExecutionService._monitor_simulation`,
  which decided status from the return code alone and forced 100 %; the panel's
  sidecar reader was reachable only from a path these runs never took.
- **Fix:** both sides. `run_outcome.py` reads `Result/run_metadata.json` and
  `progress.json` (`RunOutcome.failed`, `.ended_early`, step text, progress
  fraction). Failed: red Failed, "FAILED at <t> of <T>: <reason>", progress =
  fraction reached, `error_message` set, dialog once per session and only for
  runs seen running. Old failed runs are relabeled on load without a dialog.
  Runs ending at a physical endpoint stay Completed with "Completed: ended early
  at <t> of <T> (<reason>)" (Jeff's decision).

## Logs tab and Export Logs

- Logs tab replaces the session-only event list (events now go to `thames.log`):
  summary markup from the sidecar (status, reason, diagnostics, versions), tail
  of the operation log (200 lines, read backwards in 64 KB blocks), Refresh,
  throttled auto-refresh (5 s) while running.
- Export Logs zips the operation's logs, `input.in`, `<name>_input.txt`,
  `Result/run_metadata.json`, plus the app's `thames.log`/`thames-crash.log`;
  hostname replaced by `<hostname>` when the preference is off.
- `.github/ISSUE_TEMPLATE/bug_report.md` asks for that zip.

## Paned-divider bug (found in Jeff's test)

The details pane is packed `pack2(details_frame, False, False)` (`shrink=False`),
and a notebook is as wide as its widest page, visible or not. Unwrapped labels
(the Logs file path, then the Operation Details "Current Step" holding the new
failure text) set a large minimum width and pinned the divider. Fixed with
ellipsize (path) and `WORD_CHAR` wrap + `max_width_chars` (summary, all
Operation Details values).

## Release

- Published 2026-11-23T21:12Z:
  https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.4.4 (prerelease).
- macOS zip 673,846,201 bytes, SHA-256 `0b86df7e…0403` (bundled backend ran the
  Ca11mM fixture, exit 0, 6.0.1; app launched on a scratch HOME). Windows
  installer 623,566,522 bytes, `1b570716…bdf7c` (Jeff; failure path smoke-tested).
- Release notes list the Known Limitations by release, which settles the
  "13–14 from alpha-4.2" ambiguity (alpha-4.2 reused those numbers).
- New Known Limitation ("a hydration run that fails can be shown as Completed,
  100 %") added to the alpha-2 (13), alpha-3 (20), 3.1 (20), 4 (22), 4.1 (25),
  4.2 (22) and 4.3 (18) pages; only additions, all still published.

## Pitfalls

- `pre-session-sync.sh` aborts on untracked files; do its steps by hand
  (backup branch, `pull --rebase --autostash`, `submodule update`).
- alpha-3's release body is CRLF except an LF Downloads block: splice new text
  into the raw bytes rather than normalizing.
- `gh` run outside the repo needs `-R jwbullard/THAMES`.
- Bundled `bin/thames` differs from `bin/thames` byte-wise (libpng install name
  rewritten); verify it by running it, not with `cmp`.

## Next

- 4.4 installed as `~/Applications/THAMES.app` (2026-11-23), ready for Ep 9.
- alpha.5 after the series (`docs/UI-Issues.md`); Strain Energy visualization
  to investigate before the next release.

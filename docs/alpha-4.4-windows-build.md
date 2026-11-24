# Alpha-4.4 Windows build handoff (2026-11-23)

Written on macOS for the follow-on Windows session. Project memory is keyed to
the working-directory path, so the Windows session will **not** see the mac
session's memories; this file carries everything needed.

## REBUILD 2026-11-24: replace the published 4.4 assets (do this first)

alpha-4.4 was published 2026-11-23 (tag at `fde54f52`). Jeff found that the
Operations page's **Pause** button did nothing, and decided to fix it and
**replace the assets in place** (same version, no bump; each asset had 1
download). UI-only; results cannot change.

What changed (`operations_monitoring_panel.py`, commit after `288010b3`, see
`git log`):

- **Pause / Resume work again** (broken since at least alpha-3). Hydration runs
  are launched by `THAMESExecutionService`, so the operation had no process or
  PID and Pause only logged a failure. Pause now finds the `thames`/`micgen`
  process running in the operation folder (as Stop does) and uses psutil
  `suspend()`/`resume()`. **On Windows this is the first time Pause can work at
  all** (the old code used SIGSTOP/SIGCONT, which Windows lacks); psutil suspends
  the process's threads there.
- The status bar reports "Paused / Resumed / Could not pause <name>".
- A paused run stays Paused through the database refresh (the DB records it as
  RUNNING).
- Stop is enabled for a paused run and resumes it before stopping it.
- Delete refuses paused runs as well as running ones.
- The two dead `Operation.pause_process`/`resume_process` pairs were deleted.

Steps on Windows:

```bash
./pre-session-sync.sh                     # main must include the Pause commit
git submodule update --init               # submodule stays at a27385f (6.0.1)
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

No backend rebuild (`bin\` is already 6.0.1 from yesterday) and no version
change. Smoke test (install over the current 4.4), on a hydration run long
enough to watch:

1. Pause: status Paused, status bar "Paused <name>", Duration freezes; the
   Logs tab tail stops growing for 10-20 s (Task Manager shows `thames.exe`
   at 0 % CPU).
2. Pause again: Running, continues; Duration excludes the paused time.
3. Pause, then Stop (still enabled): Cancelled within a second or two.
4. Pause, then Delete: refused with "Cannot delete running or paused ...".

Then copy `dist\THAMES-1.0.0-alpha.4.4-win64-setup.exe` to the Mac's `dist/`
and record its size and SHA-256 below. On the Mac: rebuild the zip, upload both
assets with `--clobber`, move the tag with `git push --force origin
v1.0.0-alpha.4.4` (never delete it: that turns the release into a draft), add a
dated note to the release body and notes file, asking Jeff before each GitHub
change.

| New Windows installer (Pause fix) | (fill in: commit built from, size in bytes, SHA-256, smoke-test result) |
|---|---|
| New macOS zip (Pause fix) | (filled in on the Mac) |

## Status

| Item | State |
|---|---|
| Source | pushed; `main` at `ff91efbe` or later |
| Version strings | already `1.0.0-alpha.4.4` in `app_info.py`, `installer/thames-windows.iss` (version + display "1.0.0 (alpha 4.4)"), and the macOS block of `thames-windows.spec` |
| Backend | **changed**: submodule `a27385f` = THAMES-Hydration **6.0.1**. The Windows `bin\` must be rebuilt |
| macOS artifact | in progress on the Mac (zip + draft prerelease) |
| GitHub release | not yet created; the Mac creates the draft |
| Windows installer | to build (this session) |
| Release notes | `release-notes-alpha-4.4.md`, being written on the Mac. Nothing to do on Windows |

## What alpha-4.4 is

A patch Jeff needs before recording more tutorial episodes (list in
`docs/UI-Issues.md`, alpha.4.4 section).

- **Failed runs show as Failed.** A hydration that stopped on a GEMS failure
  ("GEMS solver exceeded maximum consecutive failures") used to show
  Completed / 100 %, because the backend exited 0 after recording the failure
  and the UI ignored `Result\run_metadata.json`. Fixed on both sides:
  - Backend 6.0.1 (`a27385f`): exits 1 when `run_metadata.json` records a
    failure (`runmeta::recordedExitCode()` in `RunMetadata.{h,cc}`, used at
    the end of `deleteDynAllocMem` in `thames.cc`).
  - UI: new `src/app/utils/run_outcome.py` reads the sidecar and
    `progress.json`. The execution services and the Operations panel use it,
    so a failed run shows Failed, Current Step "FAILED at <t> of <T>:
    <reason>", and progress = fraction of the final time reached. Older
    failed runs are corrected when the page loads. A run that ends early at a
    physical endpoint (e.g. no more water) stays Completed with "Completed:
    ended early at ...".
- **Operations -> Logs tab:** run summary (status, reason, diagnostics,
  backend and UI versions), last 200 lines of the operation's log, Refresh,
  and **Export Logs...** (zip of the operation's logs, input, sidecar, and
  the app's `thames.log` / `thames-crash.log`; hostname replaced by
  `<hostname>` when Preferences -> include hostname is off).
- `.github/ISSUE_TEMPLATE/bug_report.md` asks reporters to attach that zip.

No platform branches in the new code. Windows-relevant spots worth a look in
the smoke test: the zip's default file name and save dialog, the
`%LOCALAPPDATA%\THAMES\logs\` paths it collects, and the backend's exit code.

## Windows build steps

```bash
./pre-session-sync.sh
git log --oneline -1                      # must be ff91efbe or later
git submodule update --init               # submodule must be at a27385f
./build-windows.sh clean                  # REQUIRED: backend changed to 6.0.1
find backend/thames-hydration -name version.h | xargs grep -h "GIT_HASH\|VERSION_STRING"
                                          # expect "6.0.1" and "a27385f6"
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller --clean --noconfirm thames-windows.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Expected output: `dist\THAMES-1.0.0-alpha.4.4-win64-setup.exe` (alpha-4.3's
was 623,551,248 bytes).

**Cautions**

- Use the `pyinstaller` inside the project venv, not a system one (Session 67).
- Working directory must be `C:\Users\jwbullard\Desktop\foo\THAMES`, not
  `C:\Users\jwbullard\THAMES` (Session 33).
- AppId unchanged, so installs upgrade in place; user data in
  `%LOCALAPPDATA%\THAMES\` is untouched.
- Several Python files are CRLF (`operations_monitoring_panel.py`,
  `thames_execution_service.py`, `hydration_executor_service.py`,
  `app_info.py`, `thames-windows.spec`); don't let an editor convert them.
- Any check that imports app modules from source runs the migrations on the
  **real** database. Set a scratch `LOCALAPPDATA` for such checks.

## Smoke test before copying the installer back

Install over the existing alpha-4.3, then:

1. Home page and Help -> About show **1.0.0-alpha.4.4**.
2. A short normal hydration (any existing microstructure, a few hours)
   completes: Operations shows Completed / 100 %, and its
   `Result\run_metadata.json` reports `thames_backend.version` **6.0.1**,
   `git_hash` **a27385f6**, `success: true`.
3. Select that run -> **Logs** tab: green "Completed" summary with the
   versions, the log tail fills the view, Refresh works, and the divider
   between the operations list and the details pane still drags both ways.
4. **Export Logs...**: the save dialog closes, the zip opens in Explorer and
   holds `<name>\thames.log`, `<name>\input.in`,
   `<name>\Result\run_metadata.json` and `app-logs\thames.log`.
5. Failure path (optional, if you have a run that fails quickly, such as the
   Mac's doomed-to-fail `HydrationOf-MyPaste-TP` setup): while it runs it
   shows Running; when it stops it shows **Failed** in red, Current Step
   "FAILED at ...", a one-time failure dialog, and progress = fraction
   reached, not 100 %.

## Publishing (back on the Mac; Windows has no `gh`)

Copy the installer to the Mac's `dist/` and record its size and SHA-256 in
the table below. On the Mac, with Jeff approving each GitHub change:

1. `gh release upload v1.0.0-alpha.4.4 dist/THAMES-1.0.0-alpha.4.4-win64-setup.exe`
2. Fill in the Windows size in the release body and in
   `release-notes-alpha-4.4.md`.
3. Publish (`gh release edit v1.0.0-alpha.4.4 --draft=false`), creating tag
   `v1.0.0-alpha.4.4` on `main`. Keep it a prerelease. Consider tagging the
   backend `v6.0.1` at `a27385f`.
4. Add a Known Limitation to the earlier published pages: a GEMS failure can
   show as Completed / 100 %; check `Result/run_metadata.json`.

| Windows installer | built 2026-11-23 from `15852faa` + the Duration fix (committed with this row), smoke-tested (all steps passed, failure path included): `THAMES-1.0.0-alpha.4.4-win64-setup.exe`, 623,566,522 bytes, SHA-256 `1b570716fe5fed3a337ed347a0d0f5bc8174159f558d02442de3252831bbdf7c`. Backend rebuilt with `./build-windows.sh clean`: 6.0.1, `a27385f6`, built 2026-11-23T19:27:39Z (GEMS3K's unused `kva2json` link failure is expected). Inno Setup failed once with "EndUpdateResource failed" (antivirus lock); a rerun succeeded. **The macOS zip predates the Duration fix: rebuild it before publishing.** |
|---|---|
| macOS zip | built 2026-11-23 from `360ca40a` (includes the Duration fix), backend 6.0.1 `a27385f6`: `THAMES-1.0.0-alpha.4.4-macOS.zip`, 673,846,201 bytes, SHA-256 `0b86df7ee1e45467ab9ecb0cfe6a9406fb54d070cb3b83fbaacdae81d9170403`. Bundled backend ran the Ca11mM fixture (exit 0, 6.0.1); app launched on a scratch HOME (version 1.0.0-alpha.4.4, no new log errors) |

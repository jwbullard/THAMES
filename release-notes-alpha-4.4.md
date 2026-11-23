THAMES 1.0.0-alpha.4.4 - Release Notes
=============================================

This patch release makes failed hydration runs visible and makes it easier to send logs with a bug report. The hydration model has one small change (version 6.0.1): when a run stops because of an error, the program now reports that error to the UI. Simulation results are unchanged. Upgrading in place preserves your database, operations, and settings, because they are located separately (%LOCALAPPDATA%\THAMES\ on Windows, ~/Library/Application Support/THAMES/ on macOS) from where the installer changes files.

### Downloads

- **Windows:** `THAMES-1.0.0-alpha.4.4-win64-setup.exe` (624 MB). Inno Setup installer; in-place upgrade over 1.0.0-alpha.4.3 preserves user data (AppId unchanged).
- **macOS (Apple Silicon):** `THAMES-1.0.0-alpha.4.4-macOS.zip` (674 MB). Unzip anywhere and drag `THAMES.app` to `/Applications`. First launch: right-click → Open (ad-hoc signed; Gatekeeper may otherwise refuse).

### Fixed since alpha-4.3

  1. **Hydration runs that failed were shown as Completed, 100 %.** When the chemical equilibrium solver (GEMS) failed repeatedly, the run stopped early, but the Operations page showed it as Completed with 100 % progress and no message. The results of such a run cover only the time before it stopped. Now the run is shown as **Failed** in red, with Current Step reading, for example, "FAILED at 5.58 h of 28.00 d: GEMS solver exceeded maximum consecutive failures", progress showing how far it got, its Duration stopped at the time it failed, and a message the first time it fails. Runs made with earlier versions are corrected when the Operations page loads them, so **check your earlier runs: any that now show Failed did not reach their final time.**

  2. **Runs that stop early for a physical reason** (for example, no water left in a sealed paste) still show Completed, because their results are valid up to that point, but Current Step now says so: "Completed: ended early at 4.00 d of 28.00 d (no more water in system)".

### New since alpha-4.3

  3. **Logs tab on the Operations page** (it replaces "Operation Logs", which listed only the app's own events for the current session). Select an operation to see:
     - a summary of how the run ended: status, reason, solver diagnostics, and the versions of THAMES and of the hydration model that made it;
     - the last 200 lines of the operation's log file, updated every few seconds while the run is going. Click **Refresh** to update it at any time.

  4. **Export Logs...** on the Logs tab saves a zip file to attach to a bug report. It holds the selected operation's log files, its input files and run summary (`Result/run_metadata.json`), and the app's own logs (`thames.log`, `thames-crash.log`). It does not include images or results, so it stays small. If you turned off "Include hostname in run_metadata.json" in Preferences, your computer's name is removed from the files in the zip.

  5. **Bug report template on GitHub.** "New issue" at https://github.com/jwbullard/THAMES/issues now offers a "Bug report" template that lists what to include.

### Known Limitations

  These still apply:
  - 1-12 from the alpha-4 release notes (13 and 14 there were fixed in alpha-4.1);
  - 13 (limestone mixes can stop after a few hours) and 14 (calcite under kinetic control) from the alpha-4.2 release notes;
  - 15-17 from the alpha-4.3 release notes.

  The alpha-4.3 release notes said "13-14 from the alpha-4.2 release notes" without saying that alpha-4.2 reused those numbers for different limitations; the list above is the complete set.

### Crash Diagnostics
  If THAMES crashes (window disappears with no message), look in:
    - Windows: %LOCALAPPDATA%\THAMES\logs\thames-crash.log and %LOCALAPPDATA%\THAMES\logs\thames.log
    - macOS:   ~/Library/Application Support/THAMES/logs/thames-crash.log and ~/Library/Application Support/THAMES/logs/thames.log
  The first contains stack traces from native crashes; the second is the regular application log.

### Reporting Bugs
  Use the "Bug report" template at https://github.com/jwbullard/THAMES/issues. Please include:
   - The version string from Help -> About (should say 1.0.0-alpha.4.4)
   - Operating system and version (*e.g*., Windows 11 24H2, or macOS 15 with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - The zip from **Export Logs...** (Operations page, Logs tab) for the operation that went wrong. If THAMES crashed before you could export, attach `thames-crash.log` and `thames.log` from the logs directory above instead.

Contact: https://github.com/jwbullard/THAMES/issues or jwbullard@tamu.edu

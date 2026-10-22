THAMES 1.0.0-alpha.4.1 - Release Notes
=============================================

This is a small patch release over 1.0.0-alpha.4 which gives the application a new look, a correct version
label, and a handful of fixes. **Simulation results do not change.** The
hydration model now reports version 6.0.0 (alpha-4 reported 5.2.0), but its
numerical behavior is unchanged: on a test case, every output file matched
alpha-4 except that `<name>_CSH.csv` gains one new column (see below).
Upgrading in place preserves your database, operations, and settings, because
they are located separately (%LOCALAPPDATA%\THAMES\ on Windows,
~/Library/Application Support/THAMES/ on macOS) from where the installer
changes files.

### Downloads

- **Windows:** `THAMES-1.0.0-alpha.4.1-win64-setup.exe` (624 MB). Inno Setup installer; in-place upgrade over 1.0.0-alpha.4 preserves user data (AppId unchanged).
- **macOS (Apple Silicon):** `THAMES-1.0.0-alpha.4.1-macOS.zip` (675 MB). Unzip anywhere and drag `THAMES.app` to `/Applications`. First launch: right-click → Open (ad-hoc signed; Gatekeeper may otherwise refuse).

### Changed since alpha-4

  1. **New look.** A new THAMES banner on the home page, a new application
     icon (window, Dock/taskbar, About dialog, and Windows installer), and a
     shorter description on the home page.

  2. **Version label.** The version shown in the bottom-right corner of the
     home page read "v10.0.0", a leftover from VCCTL. It now shows the real
     version, as Help -> About already did.

### Fixed since alpha-4

  1. **Stopped runs are now recorded as stopped** (alpha-4 Known Limitation
     13). A hydration run stopped from the Operations page now has
     `"exit_reason": "Stopped by user"` in its `Result/run_metadata.json`,
     instead of being left at `"in_progress"`, which was indistinguishable
     from a crash.

  2. **Hydration page Resolution field removed** (alpha-4 Known Limitation
     14). The field had no effect; the simulation always uses the resolution
     stored in the microstructure image. Saved settings from older
     operations that still contain the field load without complaint.

  3. **Final time in hours.** With the final-time unit set to hours, any value
     above 365 was silently cut back to 365 (for example, 672 h became 365 h).
     The limit is now 365 days in whichever unit is chosen.

  4. **Operation folders copied from Windows run on macOS and Linux.** A
     hydration operation created on Windows failed at once when its folder
     was run on macOS or Linux, because of Windows line endings in its input
     file. Windows itself was not affected.

### Added since alpha-4

  1. **`GelPorosityAllen` column in `<name>_CSH.csv`.** The existing
     `GelPorosity` column counts some C-S-H gel-pore water as part of the
     solid, so its value is lower than the gel porosity measured by NMR (for
     example, 0.24 instead of 0.40 at 28 days in a sealed w/c = 0.32 paste).
     The new `GelPorosityAllen` column reports the gel porosity on the basis used in the
     NMR literature (Muller *et al*. 2013), for comparison with measurements.
     All other columns are unchanged.

### Known Limitations

  Known Limitations 1-12 from the alpha-4 release notes still apply.
  Limitations 13 and 14 are fixed in this release (see above).

  Windows only: after upgrading over alpha-4, an existing desktop shortcut
  may keep showing the old icon. The program itself has the new icon; this
  is Windows' icon cache and clears after you sign out and back in (or
  restart).

### Crash Diagnostics
  If THAMES crashes (window disappears with no message), look in:
    Windows: %LOCALAPPDATA%\THAMES\logs\thames-crash.log
             %LOCALAPPDATA%\THAMES\logs\thames.log
    macOS:   ~/Library/Application Support/THAMES/logs/thames-crash.log
             ~/Library/Application Support/THAMES/logs/thames.log
  The first contains stack traces from native crashes; the second is
  the regular application log. If the operation folder itself exists,
  its Result/run_metadata.json will additionally record the exit
  reason and provenance identity. Please attach all three when filing
  bug reports.

### Reporting Bugs
  Please include:
   - The version string from Help -> About (should say 1.0.0-alpha.4.1)
   - Operating system and version (*e.g*., Windows 11 24H2, or macOS 15
     with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - `thames-crash.log` and `thames.log` from the logs directory above
   - Result/run_metadata.json from the affected operation directory
     under <user data>/operations/<name>/

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu

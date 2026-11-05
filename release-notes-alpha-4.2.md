THAMES 1.0.0-alpha.4.2 - Release Notes
=============================================

This is a patch release over 1.0.0-alpha.4.1 that fixes a number of problems in
the user interface, one of which affected simulation results (item 1 below).
**The hydration model is unchanged** (version 6.0.0, the same as alpha-4.1),
so any operation that did not use hydrotalcite or zeolite P gives the same
results as before. Upgrading in place will preserve your database, operations,
and settings, because they are located separately (%LOCALAPPDATA%\THAMES\ on
Windows, ~/Library/Application Support/THAMES/ on macOS) from where the
installer changes files.

### Downloads

- **Windows:** `THAMES-1.0.0-alpha.4.2-win64-setup.exe` (size TBD). Inno Setup installer; in-place upgrade over 1.0.0-alpha.4.1 preserves user data (AppId unchanged).
- **macOS (Apple Silicon):** `THAMES-1.0.0-alpha.4.2-macOS.zip` (676 MB). Unzip anywhere and drag `THAMES.app` to `/Applications`. First launch: right-click → Open (ad-hoc signed; Gatekeeper may otherwise refuse).

### Fixed since alpha-4.1

  1. **Removed spurious double-counting of phases in lists.**Hydrotalcite and zeolite P were entered twice, so selecting
     either of them as a hydration product put the same phase into
     the simulation under two different phase numbers, and both were filled
     during hydration. The 3D viewer showed the second one as an unnamed
     phase (for example "Phase 24"), and the amount of that product in the microstructure was
     probably doubled. **If you ran a hydration with hydrotalcite or
     zeolite P selected, please run it again with this release.** No other
     hydration product was affected.

  2. **Scrolling no longer changes values.** Scrolling the mouse wheel or
     trackpad while the pointer happened to rest on a number field or a
     drop-down list changed its value, without a click and often without
     being noticed (for example, a kinetic rate constant of 0.0500 became
     0.0480). Scrolling now moves the page instead. Values still change by
     typing, the arrow buttons, the arrow keys, or opening the list.

  3. **Better loading from previous hydration operation.** The list of locked
     microstructure phases at the top of the Hydration page previously include
d     hydration products from the earlier operation (C-S-H, portlandite,
     ettringite, and so on), which then could not be unchecked. It now shows
     only the phases in the starting microstructure, as for a new operation.
     The tooltip also now says that the operation reruns from the original
     starting microstructure, not from the final one.

  4. **Kinetics column on the Hydration page.** After the phase list is
     redrawn (for example, by choosing a different Cement Type), the Kinetics
     column no longer reverts to showing each phase's default model, even though the
     model you chose was still the one used in the run. It now shows your
     choice.

  5. **Pozzolanic cement type** no longer checks glass phases, silica fume or
     mullite as hydration products. None of them forms during hydration; if
     they are in the starting microstructure they are included anyway.

  6. **Phases missing from a mix are no longer dropped silently.** If a phase in a mix
     had no entry in the phase mapping, microstructure generation skipped it
     but still counted it in the total, so the other phases' amounts came out
     too low. Generation now stops with a message in the status bar.

  7. **Menus and Help.** Several items in the ≡ Tools and View menus opened
     the wrong page, and pressing the F1 key opened the wrong Help section on the Hydration
     page and those after it. Both now open the right page. Tools items that
     led nowhere useful were removed, and Elastic Moduli was added. On macOS,
     the User Manual now opens even when the web browser is not already
     running.

  8. **View → Fullscreen** can now leave full-screen mode.

  9. **Operations page.** Deleting an operation no longer writes an error to
     the log, and the "Operation deleted" message now appears.

 10. **Results page** no longer lists an incorrect `microstructure_metadata · Unknown
     Analysis` entry among the operations.

 11. **Mix Design.** Fine and coarse aggregate masses are no longer limited
     to 10 kg (the limit is now 100,000 kg, as for water). Creating a mix
     with no name now says "Mix name is required" instead of failing later
     with "Auto-save failed".

 12. **Log file size.** `thames.log` no longer grows by several lines every
     second while the Operations page is open, and it is now limited to
     10 MB plus three older copies.

 13. **Text corrections.** The Random Seed help text now says the seed is a
     negative integer (it said "0 = random"), and the hints under the
     kinetic model choice describe the Standard and Pozzolanic models more
     accurately.

### Known Limitations

  Known Limitations 1-12 from the alpha-4 release notes still apply.

  13. **Limestone mixes can stop after a few hours** with a chemical
      equilibrium failure when the `Thaumasite precursor` (`SO4_CO3_AFt`) product is checked (it is
      checked by default for the Limestone cement type) while calcite is
      under thermodynamic control and gypsum or bassanite under kinetic
      control. Workaround: uncheck `Thaumasite precursor` on the Hydration page.
      Hemicarboaluminate and monocarboaluminate still form without it.

  14. **Calcite under kinetic control can make a cement hydration operation slow and produce noisy output.** When hydrating a portland cement, having
      calcite set to a kinetic model (for example Standard) can cause a run can take
      many more time steps than usual, and the phase amounts can oscillate.
      Workaround: leave calcite under thermodynamic control for cement hydration operations.

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
   - The version string from Help -> About (should say 1.0.0-alpha.4.2)
   - Operating system and version (*e.g*., Windows 11 24H2, or macOS 15
     with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - `thames-crash.log` and `thames.log` from the logs directory above
   - Result/run_metadata.json from the affected operation directory
     under <user data>/operations/<name>/

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu

THAMES 1.0.0-alpha.4 - Release Notes
=============================================

Alpha-4 is a full release with a new hydration backend and a rebuilt
thermodynamic database. **Simulation results change.** Re-running an alpha-3
or alpha-3.1 operation under alpha-4 will not reproduce its earlier results,
and most of the changes are deliberate corrections (see "Changed since
alpha-3.1" below). Keep alpha-3 results labeled as such if you compare them
with new runs; each run's Result/run_metadata.json records the backend git
hash and the database checksum it used.

The user interface is essentially unchanged from alpha-3.1, so the workflow
is the same. Upgrading in place preserves your database, operations, and
settings, because they are located separately (%LOCALAPPDATA%\THAMES\ on Windows,
~/Library/Application Support/THAMES/ on macOS) from where the installer changes
files.

### Fixed since alpha-3.1

  1. **Sealed-mode runs no longer create water.** The kinetic transfer of
     dissolving clinker into solution previously balanced charge but not the
     moles of oxygen and hydrogen, adding about three, two, and six water molecules
     for every dissolved formula unit of C3S, C2S, and C3A, respectively.
     By 7 days a typical sealed paste
     had gained roughly 12 g of water per 100 g of solids, so it never dried
     out. Hydrogen and oxygen are now conserved exactly. Sealed pastes now
     self-desiccate: in a w/c = 0.44 portland paste the internal relative
     humidity falls to about 0.92 at 28 days. Saturated runs are affected
     only slightly. Iron from dissolving ferrite now enters solution as
     Fe(III), its oxidation state in the solid; the earlier Fe(II)
     assignment unbalanced charge and could stall a run. (Known
     Limitation 9 in alpha-3 / alpha-3.1.)

  2. **Equilibrium is computed at the prescribed simulation temperature.** The
     temperature set on the Hydration page was previously applied only to
     reaction rates, not to thermodynamic calculations, which were always
     made at 25 °C. The user-prescribed temperature is
     now applied to both. The database spans 5 °C to 81 °C (278.15 K to 354.15 K); a
     temperature outside that range is rejected at the start of the run with
     the reason recorded. Runs at 25 °C are unaffected by this fix. (Known
     Limitation 10.)

  3. **Runs that stop early now report the reason.** In earlier versions, a run that ended because no
     water or no room was left for new products was recorded as an
     unexplained failure, or left marked "in progress". The reason is now
     written to run_metadata.json, for example "Simulation ended early: no
     room to place hydration products". (Known Limitation 12.)

  4. **Low water-to-cement sealed pastes no longer stall for lack of room.**
     A sealed w/c = 0.32 paste used to stop at about 4 days (degree of hydration
     0.59) because new C-S-H had no space to precipitate. With C-S-H densification
     (Changed #3) the same paste runs to 28 days (0.70). The same holds for
     a sealed 10 % limestone blend.

  5. **Water held in fine pores no longer miscalculated.** When the menisci entered
     the sub-micrometer pores, the routines that empty and refill them
     were reporting only the last pore size they entered, so a run could be
     declared out of water while most of its pore water remained. A
     floating-point remainder also made the meniscus flicker between pore
     sizes. Both bugs have been fixed.

  6. **C-S-H composition output was frozen.** `<name>_CSH.csv` and
     `<name>_CSratio_solid.csv` were reporting the input Ca/Si (about 1.60) at every time
     in every earlier version. They now report the composition GEMS
     computes at each step.

  7. **Images and pore-size files at closely spaced output times.**
     Requested output times less than a minute apart were being written
     at too early a time or skipped entirely. That has been fixed.

  8. **The relative-humidity limit on reaction rates was never applied.**
     All kinetic models were meant to slow down as internal humidity falls,
     but the humidity was evaluated only once, before any pores existed, so
     every rate calculation kept that correction near a multiplicative factor
     of 1. It is now updated every step (see Changed #5).

### Added since alpha-3.1

  1. **Setting times.** Initial set is detected when a connected solid path
     spans the microstructure in all three directions; final set is declared
     when 80 % of the solids belong to the connected solid network.
     Times are written to `<name>_SettingTimes.csv`,
     the connected fractions over time to `<name>_Percolation.csv`, and two
     0/1 columns (InitialSet, FinalSet) are added to Microstructure.csv.
     Setting needs the particle-ID image (.pimg) that micgen writes with
     every microstructure; without it the columns are left empty. See Known
     Limitation 11 before comparing setting times with Vicat data.

  2. **Self-desiccation and humidity outputs.** `<name>_Humidity.csv` reports
     the internal relative humidity and its two parts (the Kelvin term from
     the meniscus and the pore-solution water activity), the meniscus
     diameter, and the capillary tension. The pore-size files report the
     same quantities and now count empty voxel-scale pores, which were
     previously invisible to them.

  3. **Chemical shrinkage.** `<name>_Shrinkage.csv` reports chemical shrinkage
     (about 0.057 mL per g of solids at 28 days for a w/c = 0.44 portland
     paste, within the measured range) and a provisional autogenous strain
     (see Known Limitation 10).

  4. **C-S-H gel properties.** `<name>_CSH.csv` now includes the gel porosity, solid and
     saturated gel densities, H2O/Si, the fraction of gel pores holding
     water, and the specific precipitation space used by the densification
     model.

  5. **Meniscus-corrected thermodynamics.** When menisci lower the internal
     humidity, the chemical potential of pore water is lowered to match
     before each equilibrium calculation, so hydrates that hold water become
     correspondingly less stable. `<name>_SI_MeniscusCorrected.csv` reports
     the saturation indices with this correction.

  6. **More quantities in the Results Viewer.** The Data Plots tab now also
     offers degree of hydration, pH, internal humidity, shrinkage, C-S-H
     gel properties, percolation, and the meniscus-corrected saturation
     indices. Operations run with an earlier version show only the files
     they contain.

### Changed since alpha-3.1

  1. **Rebuilt thermodynamic database.** The GEMS database was regenerated
     on a temperature grid that includes 25 °C exactly (the old grid had to
     interpolate there). The C3S and C3A solubility corrections from earlier
     releases are carried over. Equilibrium results at 25 °C shift by a few
     tenths of a percent.

  2. **Saturated runs become sealed when the capillary pores disconnect.**
     Saturated curing supplies water from outside, which can reach the
     interior only while the capillary pores form a continuous path through
     the microstructure. When that path is lost the run continues as a
     sealed run on the water it holds. In a w/c = 0.44 portland paste this
     happens at about 1 day.

  3. **C-S-H densifies as space fills.** The porosity of the C-S-H gel now
     follows the space available to it (Konigsberger, Hellmich and Pichler,
     Cem. Concr. Res. 88 (2016)), instead of being fixed by its
     composition. Early C-S-H is less dense and occupies more of the
     microstructure; late C-S-H is denser. Setting and depercolation of
     capillary porosity therefore occur earlier than in alpha-3, while 28-day
     degree of hydration is essentially unchanged.

  4. **Sealed runs empty pores from one connected water front.** As chemical
     shrinkage empties pores, the empty space now grows from a single
     connected region (as vapor entering from an air void would), largest
     pores first, instead of appearing as scattered isolated voxels.

  5. **Humidity-dependent reaction rates.** Every kinetic phase now slows
     linearly as the internal relative humidity falls below 1, reaching zero
     at 0.70 (Patel *et al*., Mater. Struct. 21 (1988)). This only matters in
     sealed pastes, and mainly at low water-to-cement ratio.

  6. **Faster simulations on larger microstructures.** Site selection for
     growth and dissolution now costs far less per cycle at large sizes. A
     100³ paste hydrated to 28 days runs about twice as fast; 200³
     microstructures, previously impractical, now complete in about half an
     hour. Results are unchanged by this.

  7. **Microstructure list on the Hydration page is alphabetical.** The
     starting-microstructure dropdown previously listed operations in no
     discernible order.

  8. **Newest operations at the top of the Operations page.** Running and
     recently created operations are now listed first instead of last.
     Clicking a column header still sorts by that column.

### Known Limitations

  1. The 3D microstructure viewer requires a working OpenGL 3.3+ driver.
     It will hard-crash on environments that lack GPU acceleration (*e.g*.,
     Sandbox-style container runs).

  2. Adaptive timestep can still collapse to very small cycle sizes at late
     ages if a soluble sulfate phase, such as Arcanite or Thenardite, or another
     minority phase drops close to zero. Recommended workaround: in
     the Hydration Products tree, click the pencil-edit icon for Arcanite
     (and Thenardite if present), change the kinetic type from Standard to
     Thermodynamic, and click OK. These highly soluble sulfates equilibrate
     with the pore fluid far faster than a simulation cycle, so kinetic
     control adds nothing physically unless those phases are fully occluded
     within another solid.

  3. Loading a 200³ microstructure in the 3D viewer can use about 5 GB of
     RAM.

  4. Clicking "Stop and Delete" on a running simulation occasionally leaves
     the `thames` or `micgen` models running briefly before they exit. Not harmful.

  5. Closing the THAMES UI while a simulation is running does NOT stop the
     simulator. The next launch will flag the operation as Cancelled even
     though the simulator may still be running. **Workaround**: use the Stop button before
     quitting, or leave THAMES open until the run finishes.

  6. The microstructure generation model `micgen` may report a non-zero exit code on some Windows machines after
     successfully writing all output files. If the output files are complete
     and readable, the result is safe to use.

  7. Windows only, on mixes that contain fly ash: the Hydration Products
     tree may auto-select amorphous glass phases (K6A2S(am), CAS2(am), and
     the other three (am) phases) even when the initial microstructure does
     not contain them. **Workaround**: uncheck (am) phases
     that are known to be absent from the initial microstructure before
     starting a hydration run.

  8. Mix Design auto-save silently rejects some validation errors; they
     appear only as DEBUG lines in `thames.log`. If a mix change does not
     seem to persist, look for "Error auto-saving mix design" in `thames.log`.

  9. The data in `<name>_Enthalpy.csv` are not heat of hydration. It reports the summed
     formation enthalpy of the whole system. Water drawn in from outside
     (saturated runs) is counted as heat, and an unexplained drift remains
     even when water is conserved. Do not compare it with calorimetry.

  10. The autogenous strain in `<name>_Shrinkage.csv` is a framework, not a
     prediction. It comes out roughly ten times smaller than measured
     values (no creep, and capillary tension acts only where pores have
     emptied). Chemical shrinkage in the same file is reliable.

  11. Setting times are provisional. The 80 % criterion for final set has
     not yet been calibrated against Vicat measurements, and at 100³ the
     detected times vary by about +/- 0.3 h from one random realization to
     another. Compare setting times between mixes only when the
     differences exceed that fluctuation, or else average several runs.

  12. The CapillaryDepercolation time in `<name>_SettingTimes.csv` is unreliable in
     sealed runs (it can appear, move by several hours, or be absent between
     otherwise identical runs). It changes nothing in a sealed run. In
     saturated runs it marks the switch to sealed curing and has been
     consistent in testing.

  13. Internal relative humidity in sealed pastes is semi-quantitative. Pore
     sizes between 0.1 μm and 1 μm are represented only approximately,
     and the finest C-S-H pores shrink in proportion rather than
     preferentially as the gel densifies. Treat *absolute* humidity values as
     approximate. Testing has indicated that relative *trends* in humidity
     changes are reasonable.

  14. Restarting a hydration run from an already hydrated microstructure
     re-equilibrates the pore solution from scratch and is not supported.

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
   - The version string from Help -> About (should say 1.0.0-alpha.4)
   - Operating system and version (*e.g*., Windows 11 24H2, or macOS 15
     with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - `thames-crash.log` and `thames.log` from the logs directory above
   - Result/run_metadata.json from the affected operation directory
     under <user data>/operations/<name>/

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu
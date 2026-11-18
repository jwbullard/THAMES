THAMES 1.0.0-alpha.4.3 - Release Notes
=============================================

This patch release addresses some UI bugs in 1.0.0-alpha.4.2.
It fixes the aggregate grading
editor and the Elastic Moduli calculations for mortar and concrete, and it
corrects how particle size distributions (PSDs) are turned into
microstructures. **The hydration model is unchanged** (version 6.0.0, the same
as alpha-4.1 and alpha-4.2), but items 1-6 below still will change results because of calculations made within the UI. In particular,
microstructures made from some materials, and elastic moduli of mortars and
concretes all can be different from what would be produced by 1.0.0-alpha.4.2. Upgrading in place will preserve your database, operations, and
settings, because they are located separately (%LOCALAPPDATA%\THAMES\ on
Windows, ~/Library/Application Support/THAMES/ on macOS) from where the
installer changes files. On first launch, THAMES updates your database: it
corrects two grading templates, gives four VCCTL cements their measured PSDs,
and makes the other changes described below.

### Downloads

- **Windows:** `THAMES-1.0.0-alpha.4.3-win64-setup.exe` (SIZE MB). Inno Setup installer; in-place upgrade over 1.0.0-alpha.4.2 preserves user data (AppId unchanged).
- **macOS (Apple Silicon):** `THAMES-1.0.0-alpha.4.3-macOS.zip` (674 MB). Unzip anywhere and drag `THAMES.app` to `/Applications`. First launch: right-click → Open (ad-hoc signed; Gatekeeper may otherwise refuse).

### Fixed since alpha-4.2 that change results

  1. **Log-normal particle size distributions (PSD) were far too fine.** Material PSDs using the Log-Normal model converted to particle sizes incorrectly when
     a microstructure was generated, so they were made with many more small
     particles than specified. For example, a cement with median 10 μm and
     σ = 2 was generated with a median near 0.7 μm. Custom and Rosin-Rammler
     PSDs were not affected. **Regenerate microstructures made from Log-Normal
     materials and rerun their hydrations.** Microstructure generation now
     also uses the PSD table shown in the Materials dialog for every PSD type,
     so what you see there is what is generated.

  2. **Measured PSDs for four VCCTL cements.** `ustype1`, `cement116`,
     `cement168` and `sacci-425` reached THAMES without their measured PSDs
     (as a Log-Normal or Rosin-Rammler model, or with no data at all). They
     now have the measured PSDs from VCCTL (`ustype1` uses cement151's, as it
     did in VCCTL). **Regenerate microstructures made from these cements, or
     from copies of them.**

  3. **Grading templates.** The standard "ASTM C-33 Fine Aggregate" template
     held the C 33 lower limits as cumulative % passing, but every calculation
     reads templates as % retained on each sieve, so most of the sand was
     treated as very coarse. "ASTM #57 Stone" put all of the stone between
     19 mm and 31.5 mm. Both now hold the middle of the C 33 grading limits.
     **Rerun Elastic Moduli for mortars and concretes that used these
     templates.**

  4. **Edited gradings were ignored by Elastic Moduli.** A grading changed in
     Mix Design → Grading… was used only if it had been saved as a template;
     otherwise Elastic Moduli used a standard template instead. The grading
     you apply is now saved with the mix and used by Elastic Moduli.

  5. **Interfacial transition zone (ITZ) width.** The ITZ width is the median
     size of the cement particles, but the file holding the cement PSD never
     reached the Elastic Moduli calculation, so the width was always the
     default 10 μm. It is now calculated from the mix's cement particle size distribution.

  6. **Aggregate volume fractions in Elastic Moduli** were computed with fixed
     densities (2650 kg/m³ for aggregates, 3150 kg/m³ for every binder)
     instead of each material's specific gravity, as Mix Design does. The
     difference is under 1 % for ordinary sand and stone, but larger for
     binders with fly ash or other light materials, and very large for
     lightweight aggregates.

### Other fixes since alpha-4.2

  7. **Grading editor.**
     - Gradings are now entered as **cumulative % passing** each sieve, as in
       ASTM C136 test reports and the C 33 limits. Leave a row blank if that
       sieve is not used. THAMES still stores and uses % retained on each
       sieve, so saved gradings and exported files are unchanged in format.
     - The plot is the usual grading chart: % passing against sieve size.
     - A value that rises on a finer sieve, or lies outside 0-100, is flagged under the table, and the buttons "Apply" and "Save As Template" will not work until
       it is corrected.
     - The coarse aggregate table now includes the No. 8 and No. 16 sieves.
     - The Preset, Type, Normalize and Smooth controls were removed.
     - Importing a grading whose % retained values add up to less than 100 no
       longer rescales them; the remainder is shown as passing the finest
       sieve.
     - Import and Export now work (Export failed with an error, Import stored
       zeros), and their file dialogs no longer stay stuck open.
     - Two unused test templates were removed.

  8. **Elastic Moduli page.** The aggregate and air values are now shown for
     information only; they always come from the mix design. ITZ
     calculations are always included when the mix contains aggregate. The button
     "Generate Input File" was removed because it wrote a file that THAMES does not use.

  9. **Operation names are no longer reused.** Running Elastic Moduli or a
     hydration again under a name that already exists used to overwrite the
     earlier run's files. THAMES now adds -01, -02, ... to make the name
     unique and displays a message to let you know when that happens.

 10. **ITZ Analysis** now shows the layer-by-layer moduli (it showed zeros).

 11. **Effective Moduli** labels are corrected ("Young's modulus", "Poisson's
     ratio", "ITZ width", ...). If concrete moduli could not be computed, the
     reason is now shown under the title.

 12. **Duplicating a material** gives the copy its own PSD. Before, the copy
     shared the original's PSD, so editing the copy's PSD also changed the
     original's, even for the protected VCCTL cements.

 13. **Materials dialog.** The log-normal "Std Dev" field is now labeled
     "σ of ln(d)", with a tooltip giving typical values (portland cements are
     about 1 to 1.5).

 14. **Mix Design.** Air content is limited to 0.15, the largest value the mix
     accepts; values between 0.15 and 0.2 used to be accepted here and then
     fail.

 15. **Smaller fix.** Elastic Moduli no longer leaves stray grading files in
     the Operations folder or writes a database error to the log on every
     run.

 16. **Database updates now run in the installed app.** Since alpha-3, the
     database updates that a release makes on first launch failed silently
     in the installed (packaged) app; they worked only when THAMES was run
     from source. This release applies them, including two from earlier
     releases: removing aggregate names left on mixes with no aggregate
     (alpha-3), and renaming glass phases to their (am) forms in material
     compositions (alpha-3; this affects only databases upgraded in place
     from alpha-2).

### Known Limitations

  Known Limitations 1-12 from the alpha-4 release notes and 13-14 from the
  alpha-4.2 release notes still apply.

  15. **Four VCCTL cements have no measured PSD:** `dh`, `clinkerhoc`,
      `clinkerotc` and `clinkerrci` (`cementhoc`, `cementotc` and `cementrci`
      in some databases). Their measured PSDs were not found in
      VCCTL either, so their microstructures are generated from a default PSD
      (median 15 μm). Do not rely on these cements for size-sensitive results.

  16. **Mixes saved before alpha-4.3 have no saved grading.** Elastic Moduli
      uses the mix's grading template, or a standard template if it has none.
      To use a specific grading, open the mix, open Grading…, click Apply,
      and save the mix again.

  17. **Opening a material whose Log-Normal PSD has no values** fills in the
      dialog's defaults (median 10 μm, σ 2), and saving the material stores
      them. Check the PSD before saving such a material.

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
   - The version string from Help -> About (should say 1.0.0-alpha.4.3)
   - Operating system and version (*e.g*., Windows 11 24H2, or macOS 15
     with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - `thames-crash.log` and `thames.log` from the logs directory above
   - Result/run_metadata.json from the affected operation directory
     under <user data>/operations/<name>/

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu

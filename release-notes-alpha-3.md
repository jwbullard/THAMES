THAMES 1.0.0-alpha.3 - Alpha Release Notes
=============================================

This is a working draft. Append entries as fixes land; finalize at release time.

For Windows testers upgrading from 1.0.0-alpha.2.1 (the intermediate hotfix
installer distributed off the alpha-2 GitHub release page): every fix in
that hotfix is included here, along with everything that has landed on
Mac and in shared source since. Mac testers still on 1.0.0-alpha.2 (the
May 2026 zip) receive all of this at once.

Fixed since alpha-2
  1. Mix Design: small system sizes (25-49) now accepted.
     Alpha-2 had a stale schema constraint that silently rejected any
     system_size value below 50 in the Mix Design panel. The "Generate"
     click appeared to do nothing - an empty operation folder was
     created but no input file was written and micgen never launched.
     The only evidence was a buried "Error auto-saving mix design"
     line in thames.log. The legacy system_size field is now bounded
     25-400 to match the per-axis system_size_x/y/z fields.
     Workaround on alpha-2: use a system size of 50 or larger.

  2. Hydration panel: kinetic-editor Save now persists to disk.
     In alpha-2, editing a phase's kinetic defaults through the
     Hydration panel's pencil-icon dialog and clicking OK appeared to
     accept the change (dialog closed, no error), but the new values
     were never written to kinetic_defaults.json. The Preferences
     dialog's identical-looking editor did write; only the Hydration
     panel entry point silently no-op'd. The Hydration panel path now
     calls set_user_default on both OK branches so the value survives
     app restart.

  3. Simulation: silica-fume Portland cycle-11 oscillation cured.
     Long alpha-2 runs of Portland + silica fume mixes could enter a
     GEMS oscillation around cycle 11 where SI(Portlandite) would spike
     above 1600 with no plateau, forcing the adaptive timestep to
     collapse and eventually killing the run. Root cause: kinetic
     transfers (Standard, PK, SaturatingRate, JMAK, CNT) wrote only to
     the solid DC moles and never adjusted the matching aqueous IC
     counterpart. GEMS reconciled by inflating bulk composition
     (spurious phantom Ca and phantom other cations), which the kinetic
     step then re-consumed on the next cycle, producing runaway SI
     values. Every kinetic transfer now routes through an atomic
     aqueous-solid transfer helper (commitSolidICTransfer) that also
     compensates charge via H+/OH-. Portlandite SI now stays bounded
     to ~1% around 1.0 in the same run.

  4. Simulation: crash on Class F fly ash + glass-phase mixes eliminated.
     Alpha-2 backends threw a DataException from parseMicroPhases when
     the microstructure contained one of the amorphous glass phases
     (C2AS, CA2S, CAS, CAS2, K6A2S). The UI names had been suffixed
     with "(am)" in a previous cleanup, but the DCH, DBR, seed database,
     and C++ hardcoded initializers still carried the bare names. The
     lookup returned an empty gemphase_data record and the backend
     refused to start. Both naming conventions were consolidated on the
     "(am)" form end-to-end; a database migration renames any bare
     glass names in existing user databases at next launch.

  5. Simulation: long fly-ash runs no longer abort mid-simulation.
     KineticController::calculateKineticStep would call exit(0) if a
     small DC pool went slightly negative during a dissolution step,
     terminating any run that got to late-age fly-ash consumption. The
     controller now clamps the dissolution amount to the available
     inventory, emits a WARNING, and continues. Verified with cem152-fa
     to 672 h (1956 cycles, 332 clamp events, exit 0) and cem151-fa-1
     (2363 cycles, 71 clamp events, exit 0) with no run-completion
     regressions elsewhere.

  6. Simulation: zero-oxide cements no longer crash during microstructure
     generation.
     Mixes based on a cement whose oxide analysis has a zero component
     (e.g. cement151 with 0% K2O) triggered a micgen SIGSEGV inside
     the rand3d correlation-file loader. The Python UI now detects
     all-zero correlation BLOBs and does not write the corresponding
     .k2o/.na2o/... file (micgen already handles the "file absent"
     case by setting the phase fraction to zero); micgen's rand3d
     additionally gained a defensive guard against a divide-by-zero
     when the derived standard deviation is below 1e-12.

  7. Simulation: cross-platform Windows portability.
     Nine sites in the Windows backend (mostly output-directory setup)
     shelled out to cp, mv, and mkdir. Windows cmd.exe does not
     provide these; the calls silently failed and the operation folder
     was left in an inconsistent state. Replaced with std::filesystem
     (C++17) helpers so the behavior is identical on macOS, Linux,
     and Windows-MinGW.

  8. Simulation: Windows link fix for gethostname in run_metadata.
     The Windows MinGW build of the backend failed to link because
     gethostname (called from RunMetadata) needs -lws2_32. Added.

  9. Simulation: micgen triple-fix.
     Cross-platform latent bugs that surfaced on Windows testers'
     machines and were traced back to shared C code. (a) A double-free
     of global arrays on a second in-process run; (b) a particle
     pointer-array out-of-bounds when the total particle count was
     smaller than the pre-allocated pool (used the pool size instead
     of the actual count as the loop bound); (c) an fclose-before-rename
     sequencing error that occasionally left a partial file when
     write_micgen_output finalized on Windows.

 10. Simulation: crash provenance recorded even for early failures.
     Alpha-2's exit_status.json was written only in specific catch
     blocks. Crashes during ChemicalSystem construction (e.g. the
     Class F fly ash issue above) left no machine-readable exit record
     at all. The new run_metadata.json is now initialized before
     ChemicalSystem construction and finalized in every reachable
     catch block plus a top-level fallback, so every failed run
     records at least "exit_reason" and DCH sha256.

 11. UI: crashed operations now show FAILED, not "Pending 0%".
     The Operations Monitoring panel's status-mapping table was
     missing the "ERROR" alias used by the backend crash writer; the
     mapping fell through to PENDING and a subsequent polling pass
     zeroed the progress. Any operation the backend marked as failed
     now surfaces correctly in the UI.

 12. UI: Load Operation restores the microstructure file selection.
     Alpha-2's Load Operation populated all simulation settings but
     silently kept whatever microstructure was in the (now-disabled)
     picker. If a user loaded an old cement-mix1 operation while the
     UI was on cement-mix2, the loaded settings were applied to the
     wrong microstructure with no warning. The microstructure filename
     is now stored with the operation config and restored on load;
     legacy configs fall back to parsing line 4 of input.in, and if
     that fails the user sees a strong warning.

 13. UI: Mix Design "Create Mix" no longer opens a spurious orphan-
     aggregate warning dialog on Portland-only mixes.
     Alpha-2 auto-selected the last alphabetical fine and coarse
     aggregate on Mix Design panel load. Every new Portland-only mix
     therefore silently persisted fine_aggregate_name and
     coarse_aggregate_name to real materials with mass = 0, and
     Create Mix then popped a warning dialog on every click. The
     aggregate dropdowns now default to the "-- Select --" placeholder;
     concrete-mix users make one dropdown click; Portland-only users
     never see the dialog. See also Changed #3.

 14. UI: 3D viewer Color button no longer crashes in developer-mode
     launches.
     A GLib abort from a missing org.gtk.Settings.ColorChooser schema
     killed the UI when the color picker was opened from a source-run
     THAMES on macOS under Ghostty. Bundled builds were unaffected.
     Source-run macOS launches now set GSETTINGS_SCHEMA_DIR to the
     Homebrew glib share path.

 15. UI: phase-connectivity calculator no longer reports non-percolating
     phases as fully percolated.
     The Results-panel connectivity dialog reported anhydrous grains at
     ~5% volume fraction as percolating in every direction, which is
     physically impossible (3D site-percolation threshold on a simple
     cubic lattice is ~31%). Root cause: the directional-percolation
     test ran on labels that had already been merged across periodic
     boundaries, so any two isolated grain cores that happened to sit
     at matching (z,y) positions on opposite faces of the box got
     stitched into one component that trivially "touched both faces."
     Cluster-size statistics still use periodic-merged labels (a
     cluster that wraps the box IS one cluster in an infinite-tiled
     sample); the percolation test now uses non-periodic labels. A
     new metric, "Percolated Fraction," replaces the older
     "Percolation Ratio" (which was actually a largest-cluster fraction,
     not a percolation metric).

Added since alpha-2
  1. Provenance sidecar (run_metadata.json).
     Every operation now writes Result/run_metadata.json containing a
     machine-readable record of the THAMES version and git revision,
     build date, compiler and CXX_FLAGS, DCH file sha256, exit reason,
     and UI context (Python version, hostname, platform). Each result
     CSV also gets a "#"-prefixed comment header carrying the same
     identity. The older exit_status.json is retired; existing tools
     that read it should switch to the new sidecar.

  2. Preferences: Include hostname in metadata toggle.
     Some users prefer their machine name not appear in provenance
     records; a checkbox in Preferences -> General controls it. Default:
     on.

  3. Database migrations run at app launch.
     Schema updates authored by future THAMES releases now apply
     automatically the first time the UI starts after the update.
     Idempotent and fail-safe: a broken migration is logged, and the
     app still launches so the user can act on the message. This
     closes an alpha-2 latent gap where the migration authoring path
     existed but was never actually called.

  4. Classical Nucleation Theory (CNT) infrastructure -- opt-in per
     phase.
     StandardKineticModel and PozzolanicModel can now place hydration-
     product voxels via a physically-parameterized nucleation
     model (interfacial energy gamma, prefactor A_0, contact angle
     theta, molar volume V_m). Off by default; enable per phase by
     adding a "nucleation" sub-block under "kinetic_data" with the
     four parameters. See docs/session50_summary.md for calibration
     and prototype notebook pointers.

  5. SaturatingRateModel kinetic class -- opt-in per phase.
     A new kinetic class implementing the saturating rate law
     r = k (1 - exp[-(-B ln Omega)^n]), from Bullard 2015 CCR Eq. 2
     and Han et al. 2025 CEJ Eq. 7. Asymmetric dissolution / precipitation
     parameters. Enable with kinetic_data.type = "SaturatingRate"
     and a matching parameter block. See docs/SATURATING_RATE.md.

  6. JMAK-per-voxel growth kinetics -- opt-in per phase.
     Kolmogorov-Johnson-Mehl-Avrami growth applied at each electrolyte
     voxel, giving sub-voxel resolution for advection-limited product
     growth. Enable with kinetic_data.type = "JMAK" and {n, alpha}
     parameters. The moment-decomposition derivation for time-varying
     nucleation and growth rates is documented at
     docs/jmak_moment_decomposition.tex.

  7. Transport-controlled kinetics correction -- opt-in per phase.
     Per-site shell-thickness delta is estimated from lattice topology
     via a ball-centroid outward-normal method; an optional "transport"
     sub-block under "kinetic_data" applies a diffusion-resistance
     factor to the Standard, SaturatingRate, and Pozzolanic dissolution
     rate. Off by default; when the block is absent, the correction
     factor is 1 (unchanged behavior).

  8. Mass balance in kinetic transfers.
     Every kinetic path (Standard, PK, SaturatingRate, JMAK, CNT) now
     routes solid-side inventory changes through a single helper that
     also updates the aqueous IC side with H+/OH- charge compensation.
     Prevents the phantom-species conditions that caused several
     alpha-2 oscillation and runaway problems (Fixed #3 above is one
     of these).

Changed since alpha-2
  1. GEMS thermodynamic database: corrected G(C3S) to reconcile with
     experimentally-inferred equilibrium constant.
     The default CemData18 values (Babushkin heritage, extrapolated from
     clinker-formation calorimetry to 298 K via estimated Cp) gave
     ln K = -24.4 for C3S + 5 H2O <=> 3 Ca2+ + H4SiO4 + 6 OH- at 298.15 K,
     ~11 orders of magnitude larger in K than the value ln K = -50.7
     inferred by Nicoleau et al. from dissolution rate measurements.
     Under GEMS's original K, C3S saturation indices in real cement paste
     aqueous states were spuriously large, and the SaturatingRateModel
     (calibrated against Nicoleau's data by Bullard 2015) predicted
     near-full-rate dissolution even in near-equilibrium regimes where
     experiment shows rate approaches zero.
     Fix: constant offset of -65,211.81 J/mol applied to G(C3S) at all
     39 T grid points in src/data/gems/thames-dch.dat. Physically
     attributed to a Cp-integration error in Babushkin's low-T
     extrapolation (H error, S preserved). H0 and S0 arrays not
     shifted; enthalpy-of-hydration tracking for C3S will still reflect
     Babushkin values (separate concern, deferred).
     Verified: ln K at 298.15 K bracketed to -50.70 exactly; SI(C3S)
     shifts by factor exp(26.3) uniformly; other phases unchanged;
     GEMS3K parses and runs cleanly. Backup preserved at
     src/data/gems/thames-dch.dat.pre-c3s-lnK-fix-20260731.

  2. GEMS thermodynamic database: corrected G(C3A) to reconcile with
     experimentally-inferred equilibrium constant.
     The default CemData18 values (same Babushkin heritage as C3S) gave
     ln K = +34.6 for C3A + 2 H2O <=> 3 Ca2+ + 2 AlO2- + 4 OH- at
     298.15 K, ~36 orders of magnitude larger in K than the value
     ln K = -48.75 measured by Ye et al. 2022 via digital holographic
     microscopy dissolution-rate extrapolation to zero rate. The
     unphysical GEMS value would require ~45 M Ca2+ at stoichiometric
     equilibrium; Ye's value corresponds to ~5 mM Ca2+, consistent with
     C3A dissolution experiments. Ye 2022 explicitly notes their
     measurement is "dozens of orders of magnitude smaller than [prior
     thermodynamic-database calculations]".
     Fix: constant offset of -206,549.59 J/mol applied to G(C3A) at
     all 39 T grid points in src/data/gems/thames-dch.dat (line 681,
     DC index 117). Matches Ye 2022 exactly at 298.15 K; residuals
     +/-0.5 ln units at 20-40 C (Ye's calibration range); larger
     residuals outside that range preserve GEMS's own temperature
     dependence rather than extrapolating Ye's 4-point fit into
     unconstrained regions (three candidate models diverge by up to
     22 ln units above 40 C).
     Practical impact: C3A currently uses ParrotKilloh in production,
     which does not consume SI, so no simulation results change today.
     But the correction is prerequisite before migrating C3A to
     Standard or SaturatingRate kinetics; without it, SI(C3A) in real
     paste would be ~10^36 and dissolution rate would run at maximum
     everywhere.
     Verified: ln K at 298.15 K interpolated to -48.75 (target -48.75);
     all other phases unchanged (C3S -50.70, Portlandite -5.20 log
     units, sulfates within 0.005 units). Backup preserved at
     src/data/gems/thames-dch.dat.pre-c3a-lnK-fix-20260806.

  3. Mix Design panel: aggregate dropdowns default to placeholder.
     Alpha-2 auto-selected the last alphabetical fine and coarse
     aggregate on panel load. This produced two visible symptoms:
     (a) a spurious warning dialog on every Create Mix click for
     Portland-only mixes (fine_aggregate_name persisted while mass was
     zero); (b) subtle downstream side effects when a user assumed the
     Portland-only mix carried no aggregate metadata but the persisted
     name flowed into the phase-ID mapping. The combos now default to
     the "-- Select --" placeholder; concrete-mix users pick an
     aggregate explicitly, Portland-only users are not harassed. Any
     mix design still carrying orphan aggregate names from an earlier
     THAMES session gets cleared on the first launch of alpha-3 via a
     one-time schema migration.

  4. KineticController: DC-depletion behavior changed from abort to
     clamp-and-continue.
     Previously exit(0) if a small solid DC pool would have gone
     slightly negative during a dissolution step. Now clamps to the
     available inventory, emits a WARNING to the log with the DC name
     and phase, and continues. A different failure mode
     (scaledMass < 0, kept as a genuine simulation-death signal) now
     calls runmeta::finalize with a specific reason before exit(1)
     so the provenance sidecar records it.

  5. Connectivity analysis: percolation test uses non-periodic labels,
     cluster-size statistics use periodic-merged labels.
     Two labeling passes per phase; the percolation test correctly
     reflects the physical question "is there a connected wall-to-wall
     path?" while cluster-size statistics correctly reflect the
     infinite-tiled interpretation. A new metric, "Percolated Fraction"
     (fraction of the phase's voxels that reside in a percolating
     cluster), replaces the older "Percolation Ratio" (which was a
     largest-cluster fraction, not a percolation metric). User-facing
     terminology switched to "cluster" throughout for consistency with
     "component" as reserved for mix-design constituents.

  6. Hydration-product defaults: duplicate hydrotalcite alias removed
     from slag cement defaults.
     The slag cement type's default suggested-products list previously
     contained both "hydrotalcite" and "OH-hydrotalc" as UI entries,
     both mapping to the same GEMS phase (gems_name="OH-hydrotalc",
     Mg-Al layered double hydroxide). The "OH-hydrotalc" alias entry
     is removed; the "hydrotalcite" entry survives and still applies
     to both slag and blended cement types. Portland and other cement
     defaults unchanged.

  7. Amorphous glass phase names in GEMS DCH: renamed to (am)-suffixed
     variants.
     C2AS, CA2S, CAS, CAS2, and K6A2S were renamed to C2AS(am),
     CA2S(am), CAS(am), CAS2(am), K6A2S(am) to reflect their amorphous
     character and to align with the UI convention adopted in an
     earlier cleanup. The rename propagates through the DCH, DBR, seed
     database, Python UI, and C++ hardcoded initializer blocks. An
     idempotent database migration renames the same phases in any
     pre-existing user database on first launch of alpha-3.

Known Limitations
  1. The 3D microstructure viewer requires a working OpenGL 3.3+
     driver. It will hard-crash on environments without GPU
     acceleration (e.g. Sandbox-style container runs).

  2. Adaptive timestep can still collapse to sub-ms cycle sizes at
     late ages if a sulfate phase (Arcanite, Thenardite) or any other
     small-inventory phase drops close to zero. The alpha-3 clamp
     (Fixed #5, Changed #4) prevents the outright abort in this
     regime, but the slowdown can persist. Workaround: uncheck those
     phases in the Hydration Products tree before starting a long run.

  3. Loading a 200^3 microstructure in the 3D viewer can use ~5 GB RAM.
     Stay at 100^3 for alpha testing unless you have plenty of memory.

  4. Clicking "Stop and Delete" on a running simulation occasionally
     leaves thames or micgen running briefly before they exit. Not
     harmful (check Task Manager or Activity Monitor if unsure).

  5. Closing the THAMES UI while a simulation is running does NOT stop
     the underlying simulator process. The next UI launch will flag the
     operation as Cancelled even though the simulator may still be
     running. Use the Stop button before quitting, or leave THAMES open
     until the run finishes. Completed runs are still visible in the
     Results panel.

  6. micgen may report a non-zero exit code on some Windows machines
     after successfully writing all output files. Outputs are usable.
     A pass of latent-UB fixes in alpha-3 addressed several of the
     cases responsible; if you still see a nonzero exit and the output
     files are complete and readable, the result is safe to use.

  7. Windows only: the Hydration Products tree in the Hydration panel
     may auto-select amorphous glass phases (K6A2S(am), CAS2(am), and
     the other three (am) phases) as suggested products even when the
     initial microstructure does not contain them. The resulting
     simparams.json for the same UI inputs is not byte-identical to
     the macOS output. Aqueous SI for these phases is low in Portland
     pore solution so user-visible physics divergence is unlikely, but
     not proven zero. Workaround: uncheck any unwanted (am)-suffixed
     glass phases in the Hydration Products tree before starting a
     hydration run.

  8. Mix Design auto-save silently rejects some Pydantic validation
     errors -- they end up as DEBUG lines in thames.log rather than as
     user-visible warnings. Workaround: if a mix change does not seem
     to persist, check thames.log for "Error auto-saving mix design"
     lines near the timestamp of your action.

Crash Diagnostics
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

Reporting Bugs
  Please include:
   - The version string from Help -> About (should say 1.0.0-alpha.3)
   - Operating system and version (e.g. Windows 11 24H2, or macOS 15
     with chip type from Apple menu -> About This Mac)
   - Steps to reproduce
   - thames-crash.log and thames.log from the logs directory above
   - Result/run_metadata.json from the affected operation directory
     under <user data>/operations/<name>/

Contact: https://github.com/jwbullard/THAMES/issues
         or jwbullard@tamu.edu

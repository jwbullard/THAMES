THAMES 1.0.0-alpha.3 - Alpha Release Notes
=============================================

This is a working draft. Append entries as fixes land; finalize at release time.

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

Added since alpha-2
  (none yet)

Changed since alpha-2
  1. GEMS thermodynamic database: corrected G°(C3S) to reconcile with
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
     Fix: constant offset of -65,211.81 J/mol applied to G°(C3S) at all
     39 T grid points in src/data/gems/thames-dch.dat. Physically
     attributed to a Cp-integration error in Babushkin's low-T
     extrapolation (H° error, S° preserved). H0 and S0 arrays not
     shifted; enthalpy-of-hydration tracking for C3S will still reflect
     Babushkin values (separate concern, deferred).
     Verified: ln K at 298.15 K bracketed to -50.70 exactly; SI(C3S)
     shifts by factor exp(26.3) uniformly; other phases unchanged;
     GEMS3K parses and runs cleanly. Backup preserved at
     src/data/gems/thames-dch.dat.pre-c3s-lnK-fix-20260731.

  2. GEMS thermodynamic database: corrected G°(C3A) to reconcile with
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
     Fix: constant offset of -206,549.59 J/mol applied to G°(C3A) at
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

Known Limitations
  (carry forward applicable items from alpha-2 at release time;
  remove items that have been fixed in this release)

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

Known Limitations
  (carry forward applicable items from alpha-2 at release time;
  remove items that have been fixed in this release)

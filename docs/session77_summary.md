# Session 77 (Oct 2-3, 2026): C-S-H densification landed, generality-tested

Continuation of S76. Jeff agreed to all five densification decisions; step 2
(gel porosity from available space) and a parameter-free gel-envelope rule
landed, were tested on five pastes, and were pushed. Also fixed the MSMSE
Fig. 9 image-timing bug. Commits: submodule `2110309`, `e6312b6`; super-repo
`13163f69`, `46755d44`. All pushed.

## MSMSE image-timing bug (submodule `2110309`)

Jeff's new DEFERRED entry from the manuscript revision: with outputs under a
minute apart, images and pore-size files were written early and labeled with
the output time (`thrTimeToWriteLattice = 0.0167` h). Set to 1e-9 h, a
rounding tolerance rather than zero, because
`lastGoodTime_ + (outTime - lastGoodTime_)` can land one ulp short. A probe
confirmed `abs(double)` resolves to the double overload, so there was no
integer truncation on top. Ca11mM fixture byte-identical, images included.
The MSMSE frozen build is `c6f84fb` (S38): none of the later fixes are in the
manuscript runs, and `_CSH.csv` Ca/Si there is the frozen input-DBR value.

## Step 2: gel porosity follows available space (submodule `e6312b6`)

- **phi vs psi, clarified for Jeff:** phi is a property of the C-S-H (gel-pore
  fraction of a CSHQ voxel); psi is a property of the paste (all liquid water
  over Allen-solid C-S-H plus that water). They coincide only in regime III,
  on the Allen basis.
- `GelDensificationParameters.h` (new): Konigsberger 2016 Eq. 42 (regime II)
  and Eq. 13 (regime III), onset value held above psi 0.942 (Muller: earliest
  C-S-H least dense); exact conversion to the GEMS-solid basis
  `phi = (rho_s - rho*)/(rho_s - rho_w)`, clamped [0, 0.99]. phi reaches 0 at
  psi = 0.221 for rho_s = 2.25 (I said ~0.3 earlier; wrong).
- `ChemicalSystem::calcCSHPsi`: the one psi computation, shared with
  `_CSH.csv`. Optional `gel_densification` JSON block; `enabled: false`
  byte-identical to the previous binary. `corPorCSHQ` deleted.
- **First result exposed a flaw:** at w/c 0.32 the average-density target
  dissolved C-S-H voxels after 160 h (volume 0.457 -> 0.438), Kelvin RH back to
  0.993.

## The gel-envelope rule

Jeff's challenge: make sure rules generalize, not fit one run. My first
statement ("envelope never shrinks") would have blocked C-S-H dissolution under
carbonation/leaching, and the unit test then exposed a second gap (dissolving
gel could expand outward). Final rule, parameter-free:

- solid growing -> envelope may not shrink (may grow);
- solid shrinking -> envelope between proportional shrink and unchanged.

Committed only on accepted steps (`commitCSHEnvelope` in Controller), because
`calculateState` also runs on rejected attempts. Logic in
`densifiedGelPorosity()` so it is unit-tested:
`unit_tests/test_gel_densification.cc`, 19 hand-computed checks (one of my
expected values was wrong, caught by the test).

## Generality tests (same binary, same rules)

| Case | DOR off / on | Set off -> on (h) | Note |
|---|---|---|---|
| w/c 0.32 sealed | 0.587 (stops 96 h) / 0.697 | 2.02/3.38 -> 1.41/2.40 | envelope holds C-S-H |
| w/c 0.443 sealed | 0.793 / 0.796 | 2.63/4.43 -> 1.64/3.07 | envelope never binds (byte-identical) |
| w/c 0.443 saturated | 0.796 / 0.796 | 3.20/4.74 -> 2.07/3.10 | depercolation 49 -> 21 h, switch fires |
| fly ash saturated | 0.730 / 0.730 | 2.22/7.56 -> 2.04/4.24 | outside fit, stable |
| 10 % limestone sealed (`cem151-w32-0p1LS`) | 0.588 (stops 100 h) / 0.734 | 1.81/3.20 -> 1.19/2.38 | calcite reacts |

DOR unchanged wherever both ran full length; densification changes
microstructure, not chemistry. Gel density lies on Eq. 42 until the envelope
binds.

## What did not work, and why

- **Restart-from-hydrated-image carbonation:** GEMS re-equilibrates the 28 d
  image (portlandite 0.117 -> 0.223) and calcite has no room. Not a supported
  path.
- **Fixed CO3-2 in sealed paste:** hundreds of GEMS AIA failures with
  densification on AND off; a failure inside `calculateSI` is fatal. Filed.
- **Setup errors of mine:** first limestone set copied GEMS files from the UI
  op folder, which held the alpha-3 database (no 298.15 K grid point);
  Jeff's UI launch used `dist/THAMES.app` (alpha-3 backend). Both rerun.

## Docs

- `docs/DEFERRED.md`: five new entries (calculateSI GEMS failure fatal;
  GEMS-exception provenance gap; fixed CO3 in sealed paste ill-posed; sealed
  densified runs never register capillary depercolation; `_CSH.csv` Ca/Si = 1
  at t = 0), after Jeff's three research directions, all committed in
  `46755d44`.
- `docs/gel_densification.tex/.pdf` + figures + figure script: Jeff's
  eyes-only explainer with file:line references at `e6312b6`. **Left
  untracked deliberately.**

## Next

- Step 4: remove the largest gel pores first when phi drops (controls the
  meniscus).
- Restamp `wmc0_` on CSHQ sites when phi changes.
- The original question: w/c 0.32 now reaches 672 h, so test gel-water
  drawdown (`GelPoreSaturation`, internal RH).
- A deliberately designed open-boundary carbonation or leaching case for the
  envelope shrink branch.

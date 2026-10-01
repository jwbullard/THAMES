# Session 75 (Sep 30, 2026): GEMS database rebuild reconciled, verified and installed

Single-thread session. The whole of it served one end: get 298.15 K onto the
DCH's temperature lookup grid so that Step 2 of the meniscus water-activity
correction can write `G0(H2O@)` at the temperature every simulation actually
runs at. That is now done, and the gel-water thread it was blocking is clear to
proceed.

## Where this came from

S74 implemented Step 2 of the meniscus correction
(`ChemicalSystem::applyMeniscusWaterCorrection`, submodule `5190772`) and found
it inert. The guard at `ChemicalSystem.cc:4458-4464` looks for a temperature
lookup point satisfying `fabs(T_ - TKval[j]) < Ttol`. On the old database the
grid was 2 K spaced with `Ttol = 1`, so 298.15 K sat exactly `Ttol` from both
neighbours, the strict `<` failed, `slot` came back `-1`, and the correction
warned once and skipped every step.

Widening `Ttol` or moving the run temperature was tried in S74 and made GEMS
fail at construction with an AIA convergence error — which is how the
`strainenergy` out-of-bounds read was found and fixed. With that fixed, the
remaining obstacle was the grid itself, and the GEM-Selektor project is not on
this machine. Jeff rebuilt the database at home.

## Rebuild attempt 3 — accepted

Attempts 1 and 2 are written up in the memory
`project_dch_rebuild_handoff.md`. Attempt 1 came from the wrong source project.
Attempt 2 was structurally correct but carried two extra species,
`Ca(HSiO3)+` and `Si4O10-4`; Jeff excluded both — bad experience previously,
and the database author considers the data speculative. **Their absence is not
a defect and they should not be reintroduced.**

Attempt 3 matched the current file on all five dimension counts exactly:

    nIC 14   nDC 198   nPH 100   nPS 11   nDCs 109

Grid: T 278.15-354.15 K at 2 K spacing, 39 points, **298.15 K exactly on
grid**; P 1-1001 bar at 6 points, ambient exact. `Ttol 1`, `Ptol 50000`,
`mLook 0`.

An earlier recommendation to tighten `Ptol` was **withdrawn** — at 20 MPa
spacing a 50 kPa tolerance only ever matches the exact point, so it is fine as
delivered.

## Reconciliation

Every remaining difference from the current file was proven to be a rename, by
two independent methods: identical stoichiometry rows, and identical position
in the name lists. 46 renames applied in the new-to-current direction — 17
phase, 29 DC — scoped to the `PHNL` and `DCNL` block substrings so that exact
quoted-token replacement could not collide with longer names
(`'ettringite'` vs `'ettringite05'`). The DBR carries names only in `#` comment
lines, so its 46 substitutions are cosmetic, not functional.

Then the two hand G0 corrections, keyed on DC **name** and never index,
broadcast across all 234 T x P slots each:

| DC | G0 at 298.15 K, 1 bar | offset | after |
|---|---|---|---|
| C3S | -2,784,326.0 | -65,211.81 | -2,849,537.8 J/mol |
| C3A | -3,382,346.0 | -206,549.59 | -3,588,895.6 J/mol |

Audit: `ICNL`, `PHNL` and `DCNL` identical to the old file including order;
exactly **two** G0 lines differ from the untouched export (indices 118 = C3A,
119 = C3S); all other content byte-identical to that export.

## Verification at 298.15 K

| reaction | reconciled | target |
|---|---|---|
| C3S, H4SiO4 / SiO2@ basis | **-50.70** | -50.70 |
| C3A | **-48.75** | -48.75 |
| Portlandite log Ksp | **-5.2002** | -5.2004 (untouched control) |

**A verification trap worth remembering.** C3S first read `-41.05`, which looked
like a failure. It was the wrong reaction basis: `-41.05` is the HSiO3- form and
`-50.70` the H4SiO4 form that S56 calibrated in. In GEMS's convention that is

    C3S + 3 H2O -> 3 Ca+2 + SiO2@ + 6 OH-

The file was correct; the check was not.

Portlandite is a side benefit rather than merely a control: the old file could
only produce `-5.1895` because it had to interpolate, having no grid point at
298.15 K. The new grid reproduces the CemData18 value to four decimals.

## Install and smoke test

`bin/thames` was a day older than the `strainenergy` fix and would have died at
construction on this database, so the backend was rebuilt clean from submodule
`5190772` first. Files installed over `src/data/gems/thames-{dch,dbr,ipm}.dat`
with `*.pre-dch-rebuild-20260930` backups. The repo's `.lst` manifests needed no
edit; the export's own `thames-new-*.lst` were discarded. The IPM `<ID_key>`
still reads `"Pyrr G thames-new"` — a GEM-Selektor record key, unused by GEMS3K
at runtime, left verbatim as provenance.

Note for future work in that directory: it is ignored wholesale by the `Data/`
rule at `.gitignore:227`, which matches case-insensitively on macOS. Backups
therefore need no gitignore work, but **new files placed there are untracked**.

Smoke test, Ca11mM alite fixture: exit 0 in 29 s against a 27 s baseline,
`success: true`, zero warnings, provenance sidecar reporting
`git_hash: 5190772a` and the new DCH's sha256. The DBR now runs at
`TK 298.15` / `P 100000`, both exact grid points. Chemistry unchanged -- peak
total_Si 104.8 uM against 104.6 uM, final [Ca+2] 9.858 against 9.857 mM. The
0.2 % shift is the 1 K grid change, since the old file's nearest point to
298.15 K was 297.15.

## strainenergy: the DEFERRED entry needed correcting

An entry filed earlier the same day said the index mismatch was invisible twice
over, one reason being that 298.15 K falls through to Lagrange interpolation.
Installing this database **removes that guard** — the branch reading
`strainenergy` now executes on every call. Only "stays all zeros unless sulfate
attack is active" still holds it up.

Reviewing it also turned up a second point: `ElasticModel.cc:825-826` calls
`strainenergy.resize(numDCs_, 0.0)`, which **undoes the sizing fix on the shared
global**. Callers are `ThermalStrain.cc:2764` and `AppliedStrain.cc:959`, so
exposure is the elastic and sulfate-attack paths; hydration is unaffected,
which is why the smoke fixture passes clean.

So the proper implementation Jeff wants to revisit is not mainly the index
arithmetic. It has to settle who owns the vector's shape (one writer, sized
once from `nDC * nTp * nPp`), what the broadcast semantics are, and whether
`ElasticModel` should be writing to a process-global at all instead of handing a
value to `ChemicalSystem`. Both points appended to `docs/DEFERRED.md`.

## What this unblocks, and the next run

The gel-water availability question is **still untested**, and the memory
`project_gel_water_handoff.md` now opens with the run that tests it. Two
corrections to the record carried in it:

- The 84.9 h stall at w/c 0.32 was **not** gel water. It is a DC-depletion
  clamp on Arcanite (K2SO4 fully consumed, yet still demanded because its SI is
  ~2e-5) — S66's Known Limitation #2, with a known pencil-edit workaround. My
  gel-water reading of it was wrong.
- Step 2 is now able to write, but has only been verified as far as "the
  grid-point read path constructs and runs". The smoke fixture is saturated, so
  h = 1 and the shift is zero by construction. The correction **firing** has not
  been observed.

Next session, before anything else: sealed w/c 0.32 from the UI microstructure
`cem151-w32-neat`, Arcanite and Thenardite pencil-edited to Thermodynamic, out
to 672 h, Step 2 live. Watch in order — does it pass 85 h with dt recovering;
does the gel-water reservoir draw down or does DOR freeze near 0.57 again; is
the stall asymptotic rather than a stop or a grind; and does `waterG0Shift_` go
non-zero and move phases poised near SI = 1 (`monosulf-AlFe`, `C3AH6`).

Only after that run should the three availability candidates in
`docs/DEFERRED.md` be chosen among. Step 2 goes first so that `h0` is not tuned
to compensate for a thermodynamic term that was simply absent.

## Loose end not taken

`ChemicalSystem.cc:4453-4455` still comments that "a run at 298 K writes the
297.15 K point". The rebuild made that false. One-line fix, flagged not applied.

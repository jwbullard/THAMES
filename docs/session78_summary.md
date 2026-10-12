# Session 78 (Oct 12, 2026): DEFERRED corrections, the temperature bug, the sum-tree port

Catch-up session after the MSMSE-109162 revision went to the ERDC coauthors
(Oct 10). Three items, in the order Jeff approved: correct the new DEFERRED
entries, fix the temperature bug, port the sum tree. All pushed.

Commits: super-repo `bc86a648` (Jeff's ten CCRL 168 entries), `23ef7b45`,
`a4a7cd98`, `b11498ac`; submodule `57c6484`, `dbc9751`.

## DEFERRED: two entries had mislabeled "HEAD"

Jeff's CCRL 168 entries compared the frozen `c6f84fb` with the UI app's
backend, `f7959659`. That is the **alpha-3 build of Sep 16**, not the current
code.

- **"Sealed runs gain water in the current code"** describes the S55 transfer
  bug (`94bd4b0`) that S70 fixed (`0343374`). On the current code two sealed
  672 h runs hold H and O constant to four decimals. Retitled; the real
  remaining issue is that the **released alpha-3 and alpha-3.1 binaries still
  create water** in every sealed run (and inflate `_Enthalpy.csv`).
- **"HEAD also ends sealed runs when electrolyte runs out"**: also alpha-3.
  Current code records why it stops (S74, S76) and densification lets sealed
  runs continue.
- The "298.15 K is not a grid point" entry marked resolved (S75).
- `recordFailure` gets the failure count instead of the GEMS code: confirmed
  still present (`Controller.cc:1270`).
- Committed with Jeff's three uncommitted entries (`checkICMoles` mass
  creation, `recordFailure`, sum-tree port).

## Temperature bug (submodule `57c6484`)

GEMS always ran at the DBR file's 298.15 K. `ChemicalSystem` took T from
`GEM_restore_MT` (DBR `<TK>`), and `parseDoc` never read
`environment.temperature`. Only the kinetic models (which read it themselves)
used the requested T; thermodynamics, the lattice (Kelvin RH) and the
`.report` used 298.15 K.

Reading the GEMS source turned up a second problem: GEMS uses a grid point's
data **directly** whenever T is within `Ttol` of it (`check_grid_T`,
`DC_LoadThermodynamicData`), and the DCH ships `Ttol = 1` K on a 2 K grid. So
every T except the exact midpoints would have snapped to data up to 1 K away.
The same rule restricted the meniscus correction to grid temperatures.

- `parseDoc` reads `environment.temperature`, rejects values outside
  278.15–354.15 K, sets `T_`, refreshes `DCH0_`.
- `Ttol` set to 0.01 K **in code** (`GEMS_GRID_T_TOLERANCE`, `global.h`) right
  after the database loads, so every DCH copy (each operation folder has one)
  behaves the same and the data file stays as S75 verified it.
- `applyMeniscusWaterCorrection` writes the shift into all 39 × 6 (T, P) grid
  points from a per-point baseline, so it applies at any temperature through
  interpolation.
- `thames.cc`: the constructor's `DataException` handler records the
  exception's own message in `run_metadata.json`.

Verified: 298.15 K sealed w/c 0.32 to 672 h byte-identical (43/43 files);
sealed w/c 0.443 24 h at 296.15, 297.15, 298.15, 313.15 K each report their T,
apply the meniscus correction with no warnings (including off grid), and give
Kelvin RH at d = 1000 nm equal to exp(−c/(d T)) for that T; pore [Ca]
0.53 → 0.19 mM and DOR 0.329 → 0.474 from 296 to 313 K; 360 K rejected with
the range in `run_metadata.json`. The meniscus shift is the same at every T
(R·T·ln h_Kelvin is independent of T), which is correct.

Consequence: runs made before this fix at T ≠ 298.15 K used 298.15 K
thermodynamics, including the CCRL 168 runs at 296.15 K (frozen `c6f84fb` and
alpha-3 alike).

## Sum-tree port (submodule `dbc9751`)

Each weighted site pick in `growPhase`, `dissolvePhase` and `transformPhase`
was a linear cumulative scan; picks per cycle and scan length both grow as
N³, so per-cycle cost grew as N⁶. A Fenwick tree (header-only `SumTree.h`)
mirrors the candidate weights and answers picks and weight changes in
O(log n). Ported from Jeff's MSMSE revision patch (developed on `c6f84fb`).

- **Audit:** all 20 places that change the candidate vectors are mirrored;
  none added since `c6f84fb` (moisture rule, cavities, densification don't
  touch them).
- **Exact mode (identity proof):** byte-identical to the unpatched current
  binary at C168 N = 32, 50, 100 and sealed w/c 0.32 to 672 h; self-check
  clean over ~6 M draws.
- **Pure mode is now the only mode** (Jeff's decision): exact-mode fallback
  and the old scan deleted. It was also byte-identical at N = 100 and sealed
  w/c 0.32; divergence (statistical agreement only) begins at larger N from
  near-ties. A negative weight (impossible by construction: affinity ∈ [0, 1],
  `wmc` ≥ 0) aborts with a message.
- **`THAMES_SUMTREE_CHECK`** kept: bit 1 verifies the mirror; bit 2 now
  recomputes each pick by an exact integer prefix scan (the old scan is gone).
  Statistics go to stderr only when set.
- **Unit test** `test_sum_tree.cc` (random push/swapRemove/set/rebuild, exact
  rule, boundary draws, degenerate cases) in the suite.
- **Timing (C168, 672 h):** N = 100 538 → 285 s; N = 200 completes in 31 min
  (unpatched: 20 cycles in 45 min); per-cycle cost N = 100 → 200 scales as
  N^3.0.
- **Gap:** `transformPhase` has no runnable case; the sulfate-attack fixture
  predates the current database (filed in DEFERRED).
- Worktree `~/Code/THAMES/worktrees/c6f84fb-sumtree` removed (its contents
  are exactly `c6f84fb` + the patches saved in THAMES-Tests-2026); a stale
  worktree record from an MSMSE session pruned.

## Next

- Densification step 4: remove the largest gel pores first when φ drops.
- Restamp `wmc0_` on C-S-H sites when φ changes.
- The gel-water drawdown test at w/c 0.32.
- Candidates from DEFERRED: `checkICMoles` mass creation; `recordFailure`;
  `_Enthalpy.csv` (problem 2); release-note warning for the alpha-3 water gain;
  the next performance targets after the sum tree (lattice backup/restore,
  full candidate-vector rebuilds).

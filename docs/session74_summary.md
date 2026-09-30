# Session 74 (Sep 29–30, 2026): side-by-side code review, moisture rule, meniscus water activity, low-w/c stall

A working-practice change and four technical threads. Jeff split his tmux window
to keep backend source on screen and asked to be told `file:line` *before* the
plan, so he could read the code alongside the explanation rather than only
seeing results. That is now recorded in
`feedback_cnt_supervision_and_stl.md`, generalized from the CNT thread to all
backend work.

---

## 1. Late-age nucleation-into-VOID moisture rule (landed)

The S72 decision, implemented. Four edits:

- `ChemicalSystem.h` — new `getPoreSizeDistributionRef()`, a const reference
  beside the existing by-value accessor, because the moisture test reads the
  pore-size rows and a vector-of-vectors copy per voxel is unaffordable.
- `Lattice::buildMoistPhaseTable()` — one flag per microstructure phase: does
  it still hold water? ELECTROLYTE always does, VOID never, a solid does if any
  of its sub-voxel pore rows lies below the current meniscus diameter. Built
  once per nucleation call and consulted as a lookup, since the answer depends
  only on phase and meniscus position, neither of which moves during a pass.
- `Lattice::hasMoistNeighbor()` replaces `hasPorousSolidNeighbor`. Two changes
  from the old predicate: an ELECTROLYTE neighbour now **qualifies** (it was
  excluded by `> ELECTROLYTEID`), and the solid test asks whether pores hold
  **water** rather than whether pores **exist**. `Site::isPorousSolid` deleted
  with it — it had exactly one caller.
- Both candidate scans updated, the live one in `nucleatePhaseRnd` and the
  dormant one in `nucleatePhaseAff`, kept in step deliberately.

**Result on the sealed reference: no change.** DOR 0.79333, setting times
identical, VOID at 672 h 0.034697 vs 0.034694. Two reasons, and the first is
the interesting one: adding ELECTROLYTE as qualifying made the predicate *more*
permissive early, not less; and late, CSHQ's gel pores (1–3 nm) sit far below
the ~70 nm meniscus, so CSHQ still reads as moist. The rule is better founded
in both regimes but inert at this w/c.

## 2. nucleatePhaseAff is dormant, and why the terminology is twisted

Both call sites of `Lattice::nucleatePhaseAff` are commented out one line above
the live `nucleatePhaseRnd` call. It was live through `d248f87` (florin,
2024-10-30, the commit that switched affinity to contact angle) and commented
out before `f26b8bc` (2024-12-24) with **no commit message anywhere mentioning
it**.

Jeff supplied the history: he and Florin Nita used opposite definitions. For
Jeff, CSHQ appearing on an alite surface is *heterogeneous nucleation*; for
Nita that is *growth*, and "nucleation" meant only the homogeneous case with no
preferred site. So an affinity-weighted nucleation function is a contradiction
in Nita's scheme, which is likely why it survived as a comment rather than a
deletion.

**Affinity is not lost** — it lives in `growPhase`'s roulette wheel
(`Lattice.cc:1748-1765`), weighting each candidate by the summed affinity of
its neighbours, computed from contact angle since `d248f87`. That is the
dominant path. What is lost is affinity in the nucleation *fallback*, which
fires exactly when a phase has no surface of its own — the moment substrate
choice matters most, and the moment that fixes where all later growth happens.

Decision: keep it, restore it as its own change with its own before/after.
Captured in `reference_nucleation_vs_growth_terminology.md`.

## 3. GEMS does not know about the meniscus

Jeff's question, and the answer is no. Verified three ways: no capillarity,
curvature or meniscus term anywhere in GEMS3K (every "Kelvin" in its headers is
a temperature unit); `getWaterActivity()` is `node_->Get_aDC(waterDCId_)`,
straight from the aqueous activity model; and THAMES passes a fixed
`P_ = 101325` Pa into `GEM_from_MT` every cycle.

**The Kelvin factor is the Poynting term for water.** V_w·σ/RT = 0.0292 at
σ = 4 MPa against −ln(0.9704) = 0.0300 — the same quantity. So curvature and
tension are one effect, not two.

**A pressure grid cannot fix it**, which answers Jeff's question about
rebuilding the DCH/DBR with pressure points. GEMS has one pressure per node,
applied to every phase, while an unsaturated pore has liquid and solid at
*different* pressures. Setting P = P_atm − σ shifts everything together and
gives −σ·ΔV_rxn, not n·RT·ln(h). Two further obstacles: our DCH has `nPp = 1`,
and at σ = 4 MPa the liquid is at −3.9 MPa absolute, outside the water EoS
domain. A pressure grid is still worth having for autoclave, deep-well and
crystallization-pressure work — just not this.

**The correct fix is to shift one DC, not patch each phase.** `Set_DC_G0`
exists in `node.h:1228`. Writing G°(H2O@) ← baseline + RT·ln(h) lets GEMS
re-equilibrate everything consistently: hydrates, water dissociation, solute
speciation. Patching each phase's SI is basis-dependent (portlandite
dissolution can be written to release two waters or none) and leaves water
dissociation out of equilibrium.

**Step 1 landed, report-only.** `ChemicalSystem::getMicroPhaseWaterStoich` plus
a new `<job>_SI_MeniscusCorrected.csv` emitting SI × h^n, with the per-phase
water content in a `#` comment line. Step 2 (the live correction) is on hold at
Jeff's instruction pending low-w/c results.

**What the diagnostic showed, and it was not what I predicted.** I expected
ettringite (32 H2O) to dominate; by 168 h its SI had collapsed to 0.008 and a
15 % correction to a deeply undersaturated phase changes nothing. The
consequential cases are phases poised at SI ≈ 1, where a moderate water content
flips the sign: at 672 h `monosulf-AlFe` goes 1.11 → 0.925 and `C3AH6` 0.999 →
0.834 — from precipitating to dissolving. Sensitivity is n × (closeness to
SI = 1), not n alone.

**Jeff's qualification, which sharpens it.** With CaCO3 present, carbonate
stabilizes AFt (`SO4_CO3_AFt` exists in our DCH as a `tricarb03` + `ettr03_ss`
solid solution) over monosulfate, while falling RH destabilizes AFt ~2.7× more
strongly than AFm (32 waters per whole formula unit against 12). The two
compete and RH decides — a falsifiable prediction about limestone blends, which
users run now (the S71 emergency mix was 0.9 cement133 + 0.1 NormalLimestone).
Filed as a paper idea in `project_paper_idea_rh_co2_phase_stability.md`.

**Formula-unit caveat.** DC suffixes encode different bases — `ettr` is a whole
formula unit at 32 H2O, `ettr05` a half at 16, `ettr03_ss` a third at 10.7. The
diagnostic is internally consistent (each exponent matches its own DC's basis,
which is what GEMS uses for that DC's SI) but the columns are **not** comparable
to each other. Recorded in the CSV's own comment line.

## 4. Low w/c exposes a stall, and two bugs on the way

Jeff generated a w/c 0.32 neat cem151 paste via the UI after my headless micgen
attempt mislabeled phases (below). Sealed, 28 d requested.

**Everything moved the right way and hard:** initial/final set 1.77/3.32 h
against 2.40/4.43; capillary depercolation 62.9 h against 504; Kelvin RH 0.936
against 0.970; meniscus 31.6 nm against 69.6; capillary tension 9.07 MPa
against 4.12; drained bulk modulus 12.63 GPa against 7.91.

**But it stopped at 84.9 h, DOR 0.570**, with "Ran out of water" — while 69.5 %
of pore volume still held water and the RH throttle was still at 0.79. Two
findings:

- **Provenance reporting (fixed).** `thames.cc:742` caught
  `MicrostructureException` and set `errorProgram = true` unconditionally,
  ignoring `mex.getExcp()` — the flag whose purpose is to distinguish an error
  from a deliberate stop. The sidecar recorded `success: false` /
  "No specific error reason recorded" for a run the log called a normal end.
  Now branches: a real exception finalizes with code 1 and the throwing
  class/method; a normal exit finalizes with code 0, `success: true`, and the
  exception's own description. Verified: `exit_reason: "Simulation ended early:
  no more water in system"`. This covers **every** graceful stop, not just this
  one.
- **Water accounting (fixed).** `emptySubVoxelPorosity` and
  `fillSubVoxelPorosity` overwrote their return value instead of accumulating
  it, reporting only the last bin's contribution while correctly draining
  several. The caller saw a shortfall and declared the system dry.

**The fix moved the failure rather than removing it.** With accumulation
correct the run no longer stops, but the adaptive timestep collapses to the
1e-5 h floor and DOR freezes at 0.57002. Gel water is accounted for but not
*made available*, and nothing in the chain says "this water is too tightly held
to use." Filed as a POST_ALPHA entry with three candidate approaches; it
interacts with the Step-2 meniscus correction, which supplies part of the
missing self-limiting feedback, so the two should be settled together.

**Two process errors of mine worth recording.** I launched the rerun as a
background child of the shell running the waiter, so the harness killed the
simulation along with the waiter at its 30-minute limit — no `finished_utc`,
`exit_reason: "in_progress"`. And of three "bugs" I reported in that function
pair, only the accumulation one was real: the divide-by-zero and the
fill-ordering both live in state nothing reads before it is recomputed. Jeff
found that with one question ("if it is transient, why is it being run at
all?"), which also points at the cleaner fix — delete the mutation entirely.
Filed.

## 5. micgen outside the UI silently mislabels phases

Driving micgen from an operation's saved `_input.txt` produced a microstructure
with 0.6 vol% **portlandite in the starting image**. Not a volume-fraction
error: the requested fractions were placed exactly. micgen writes the ids it is
given (2, split into 2–7, then 9, 10, 11), leaving **a gap at id 8** — its
`AGGSLAB` slot, unused in a neat paste — and THAMES requires contiguous ids, so
the UI closes the gap afterwards via
`mix_design_panel.py::_remap_phase_ids_to_sequential`. I skipped that step, so
every phase above the gap sat one id high and the simparams table read
Anhydrite/Bassanite/Gypsum as Bassanite/Gypsum/Portlandite.

Consequences: running micgen directly mislabels silently, and `<op>_input.txt`
**cannot reproduce its own operation**. Filed with three candidate fixes.

Ruled out along the way: binary version (current binary reproduces the result
exactly) and correlation files (sha256 identical). The apparent speed
difference was CPU contention with a concurrent hydration run — rerun alone,
micgen takes 1:46, matching the UI.

## 6. filehandler diagnostics

`backend/src/thamesauxlib/filehandler.c` — the 2004 NIST function shared by
micgen, elastic and the rest — reported a missing `-w` workdir as
`File  could not be created. / Please verify file name.`, an empty name and
advice pointing away from the cause. Added an early guard for a NULL or empty
filename covering all four modes, naming the likely missing argument, plus
`strerror(errno)` on the four real failure paths. **This file is CRLF**; the
first edit attempt matched nothing because the patterns used `\n`, caught by an
assertion before anything was written (the S71 lesson).

---

## Reference facts

- cem151-neat is **w/c 0.443**, essentially on the Powers limit, which is why
  sealed and saturated DOR differ by only 0.4 %. w/c 0.32 is well below it and
  cannot fully hydrate; Powers' estimate for the achievable degree is
  w/c / 0.42 ≈ 0.76 against the 0.570 reached.
- Only the Kelvin term puts pore liquid in tension; dissolved salts lower
  vapour pressure without pulling on the skeleton. A measured internal RH is
  not comparable to our Kelvin RH without dividing out the activity.
- `masterPoreSizeDist_` is ordered smallest → largest;
  `calcMasterPoreSizeDist` re-derives `volfracsat` from total water, smallest
  bin first, on every `calculatePoreSizeDistribution()` call.
- Header insertions must anchor on the end of the previous function body or the
  `/**` opening the next docblock — never on a function signature, which splits
  a docblock from what it documents.

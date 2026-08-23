# CNT Diagnosis Plan: Portlandite Zero-Placement in Pure-Alite JMAK-CH Test

**Purpose.** Executable plan for the next hands-on session (60 or 61) to diagnose why the S57 pure-alite JMAK-CH test produced zero portlandite voxel placements over many cycles despite SI(Portlandite) reaching ~4.12, where the CNT physics with the currently-calibrated parameters predicts abundant nucleation.

**Author.** Session 60 (2026-08-23) — read-only trace + scope discussion, no code changes.

**Scope guardrail** — bounded by `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/feedback_thames_scope_discipline.md` (mission-creep guardrail):
- Goal: verify the CNT/JMAK infrastructure works for **Portlandite only**.
- Explicitly forbidden: cascading into "let's calibrate CNT for phase X, Y, Z". If diagnosis reveals a scope question that would extend kinetic-product treatment beyond Portlandite + CSHQ, **stop and open a scoping discussion before proceeding**.
- Ends when either (a) infrastructure verified and portlandite trajectory sensible, or (b) diagnostic reveals a fundamental modeling gap requiring separate scoping discussion.

---

## Prior beliefs (updated by session 60 read-only trace)

The five failure-mode candidates from `docs/session58_summary.md:210` have been re-ranked by the trace. Full trace narrative lives in session 60's conversation; summary below.

| S58 Candidate | Status after trace | Why |
|---|---|---|
| 1. Hard SI threshold gate | **Ruled out** | Only equilibrium guards `S ≤ 1 → 0`; no `if (S < N)`-style gate anywhere in the CNT path. |
| 2. Rate → integer truncation | **Not lossy** | Both classical `nucleationAccumulator_` and JMAK `jmakSeedAccumulator_` retain fractional residual; deferred placement is correct integration, not truncation. |
| 3. Unit mismatch | **Dimensionally clean** at every checked arithmetic site. Needs runtime confirmation of actual `V_electrolyte`. |
| 4. Wrong Ω definition | **Ruled out** | Single linear-Ω convention; `ln S` applied exactly once inside `cnt::` functions. GEMS's `Ph_SatInd` (log₁₀) is pre-exponentiated in `ChemicalSystem::calculateSI:3244`. |
| 5. Mass-balance-vs-placement mismatch | **Wiring is present** | `commitSolidICTransfer` runs post-placement in both dispatch paths (`KineticController.cc:2295` classical, `:1210` JMAK). No override found within the CNT dispatch. |

**New front-runners surfaced by the trace:**

**A. JMAK per-cycle placement floor + growth-velocity dependency.** The JMAK path places `deltaVoxels = floor(Σ_g N_g · X_g) − jmakVoxelsInLattice_[midx]` at `KineticController.cc:1134-1137`. `X_g = 1 − exp(−Y_g / V)` starts at zero for every new generation and grows *only* via `advanceMoments` accumulating `G · dt`. If `getGrowthVelocity(Portlandite, S=4.12)` returns zero or a very small number, generations get seeded but never mature to placement. **This is the leading hypothesis** for what "zero placement" actually meant.

**B. Config sanity is unproven.** No `simparams.json` in `backend/thames-hydration/tests/` contains a `nucleation` block. The failing config lives at `~/tmp/thames-satrate-val/...` (or wherever the S57 JMAK-CH test was staged). Without eyes on that file we can't rule out trivial explanations: `useNucleationKinetics: false`, no `nucleation` block for Portlandite (→ `hasNucleation()` false → dispatch skipped), or `nucleation` supplied without `jmak` (→ classical path fires, not JMAK).

**C. A₀ moved by 5 orders of magnitude at some point.** `docs/CNT_DESIGN_DECISIONS.md §4`: default reduced from 10³⁰ (S50 Kashchiev-textbook) to **10²⁵** in a 2026-07-27 scaling-fix pass. Session 58's back-of-envelope calc (J ≈ 10²³ at Ω=4.12) assumed 10³⁰. With 10²⁵ that becomes ~10¹⁸ nuclei/(m³·s) — still enormous, still should produce voxels. But our "physics says lots should nucleate" anchor needs re-derivation at the calibration actually in force.

**D. The G4 pre-loop DC lock.** `KineticController.cc:1844-1845` zeroes DC upper AND lower limits for phases with `hasNucleation() && scaledMass<=0.0` at the *start* of each cycle. Dispatch order: lock → phase-loop → placement → raise-limits. Interaction between G4 and intra-cycle GEMS calls warrants a close read; nothing here says it's buggy, but I did not fully trace whether GEMS re-equilibrates between the lock and the raise.

---

## Step 0 — Config sanity (mandatory before touching code)

Locate the actual JSON that produced "zero placement" in S57/S58. Look under `~/tmp/thames-satrate-val/` for a JMAK-CH pure-alite operation folder. Confirm ALL five preconditions:

1. `simparams.json` top-level: `useNucleationKinetics: true`
2. Portlandite `kinetic_data` contains **both** a `nucleation` block **AND** a `jmak` block. Missing `jmak` → classical path fires instead of JMAK; missing `nucleation` → dispatch skipped entirely.
3. Portlandite `nucleation` block: `A0 > 0`, `gamma > 0`, `theta ∈ [1, 180]`.
4. Portlandite kinetic model type is one that overrides `getGrowthVelocity` (Standard, SaturatingRate, or Pozzolanic — grep the kinetic model type in the config, then confirm the override exists at `<Model>.cc:5xx`).
5. `outtimes[0]` is small enough (≤ 1e-6 days) to let the adaptive controller take a tiny first cycle — S56 documented that `dt_initial` is silently ignored (POST_ALPHA).

**If ANY of these fail, the "bug" is a config problem, not a code bug. Fix the config, rerun, and only proceed to Step 1 if the failure persists.**

---

## Step 1 — Reference physics number (paper calculation, no code)

Before instrumenting, compute the expected `J` and `voxelsPerCycle` by hand for representative SI values at the actual calibration in the config. Use the exact formulas from `NucleationRate.cc`:

- ΔG*_hom / kT = 16π γ³ v_molec² / (3 (k_B T ln S)²)
- ΔG* = ΔG*_hom · f(θ) where f(θ) = ¼(2+cos θ)(1−cos θ)²
- J = A₀ · exp(−ΔG* / k_B T)   [nuclei / (m³·s)]
- r* = 2 γ v_molec / (k_B T ln S)
- V_crit = (4/3)π r*³
- voxelsPerCycle = J · V_electrolyte · dt · V_crit / V_voxel

with A₀, γ, θ, V_m as configured in Step 0; V_voxel from lattice resolution; V_electrolyte = electrolyte volume fraction × lattice volume; T = 298.15 K unless overridden.

Tabulate for S ∈ {1.5, 2, 3, 4.12, 5, 10} and for dt ∈ {1 s, 100 s, 3600 s}. This is our truth baseline — the instrumentation is verifying the code reproduces this table, not just producing plausible-looking numbers.

---

## Step 2 — Instrumentation (targeted VERBOSE-gated logging)

Add `if (VERBOSE) std::cout << ...` statements at these specific sites. Do not add general-purpose debug prints; each addition serves a specific decision-tree branch below.

**Dispatch entry** — `KineticController.cc:2201`, log per phase: `phase_name`, `useNucleationKinetics_`, `hasNucleation()`, `jmakEnabled_[midx]`. Answers: is CNT even dispatching?

**SI value into CNT** — `KineticController.cc:1032` (JMAK path) and `StandardKineticModel.cc:543` (classical fallback), log: `S`, `std::log(S)`. Answers: does CNT see the SI we think it sees?

**Rate computation** — inside `cnt::voxelsPerCycle` (add a temporary `if (VERBOSE)` block in `NucleationRate.cc:55-66` guarded on a passed-in flag OR log at the call sites in `StandardKineticModel.cc:546-556` / `PozzolanicModel.cc:715-725`), capture: `J`, `r*`, `V_crit`, `V_electrolyte`, `V_voxel`, `dt_seconds`, returned `voxelsPerCycle`. Answers: does the rate match Step 1's paper table?

**JMAK seeding accumulator** — `KineticController.cc:1069-1081`, log: `expectedNewSeeds`, `jmakSeedAccumulator_` before and after, `nSeedInt`, count of generations created this cycle. Answers: are seeds being laid at all?

**JMAK growth velocity** — `KineticController.cc:1005-1200` region, log: `getGrowthVelocity(S)` return, `dt`, `G*dt`, generation-by-generation `Y_g` and `X_g` values. **This is candidate A's diagnostic.** Answers: are seeded generations growing?

**JMAK placement floor** — `KineticController.cc:1134-1137`, log: `Σ_g N_g · X_g`, `transformedFloor`, `transformedIntTotal`, `jmakVoxelsInLattice_[midx]`, `deltaVoxels`. Answers: is the placement floor being reached?

**Post-placement mass balance** — `KineticController.cc:1210-1219` (JMAK) / `:2295-2333` (classical), log: `nPlaced`, `perVoxelMoles`, `commitSolidICTransfer` return, `DCMoles_[dcId]` before and after. Answers: is placement being rolled back?

Guard everything on `VERBOSE`; do not commit these additions to `main`. Land them on a scratch branch or apply as a locally-tracked patch (matches the S58 style for `scratchpad/thames-cc-portability.patch`).

---

## Step 3 — Test protocol

- Config: the S57 pure-alite JMAK-CH config (from Step 0), no modifications.
- Simulation time: 3 hours (enough for SI(Portlandite) to plateau above threshold; matches session-56 JMAK-Portlandite sanity horizon).
- Run with `VERBOSE=1` (or however the flag is wired — grep `getenv("VERBOSE")` if unsure).
- Redirect stdout to a log file; extract per-cycle values via `awk`/`grep`.
- Plot: `S(t)`, `J(t)`, `voxelsPerCycle(t)`, `Σ N X (t)`, `nPlaced(t)`, `Portlandite scaledMass(t)`, `[Ca²⁺](t)`, `[OH⁻](t)` — all on one figure with shared time axis.

Expected run wall-time: ~30 minutes for 3 h simulation with logging overhead.

---

## Step 4 — Decision tree

Branch on where the trajectory first departs from Step 1's expectation.

**4A. J computed, but `voxelsPerCycle` returns ~0.**
Likely cause: V_electrolyte very small (pure-alite has little initial pore space) or r* larger than expected. Confirm by comparing `V_electrolyte`, `V_voxel`, `V_crit` against Step 1's paper values. Fix: probably a config or expectation issue, not a code bug. **Do not modify the formulas — they match `NucleationRate.cc`.**

**4B. `voxelsPerCycle` matches Step 1, but `jmakSeedAccumulator_` never crosses 1.**
Diagnosis: seeding rate below 1 seed per cycle for many cycles at the operative dt. This is *correct behavior* if the rate is genuinely low. Time-to-first-placement is `1 / expectedNewSeeds_per_cycle`. If that time is longer than the total simulation window, either (i) the rate anchor from Step 1 was wrong (recompute) or (ii) the simulation is being run too briefly (extend). **Not a bug** — but the S57/S58 test may have been terminated before first placement.

**4C. Seeds are laid (nSeedInt > 0) but `Σ N X` never reaches 1.**
This is **candidate A** confirmed. Diagnosis: `getGrowthVelocity(Portlandite, S=4.12)` returns zero or too-small. Read the Portlandite kinetic model's `getGrowthVelocity` override — is it returning a physically sensible number? For Portlandite specifically, if the model type is SaturatingRate, `getGrowthVelocity` = `k · (1 − exp(−(−B ln Ω)^n))` at S > 1; check the sign convention (paper's expression is for dissolution S < 1). If the override returns 0 for S > 1, that's the bug.

**Fix path 4C**: correct the growth-velocity expression for the precipitation branch. This is a bounded, single-phase fix — do not extend to other phases. **If the fix reveals that the CSHQ / other kinetic models have the same sign-convention issue in their precipitation branches, log it as a separate finding but do not fix it in this session** — one bug at a time, one phase at a time (parameter-proliferation guardrail).

**4D. Voxels placed, then re-dissolved on next cycle.**
Diagnosis: candidate 5 alive after all, or candidate D (G4 lock interaction). Check: does the raise-limits at `:2333` actually stick past the next `calculateState` GEMS call? Instrument `DCUpperLimit_` before and after the next cycle's GEMS solve. Fix depends on whether G4's lock is being re-imposed too aggressively.

**4E. Everything works, portlandite trajectory reproduces textbook induction→acceleration story.**
**Success.** Update `CLAUDE.md` S57 entry to remove the "bootstrap deadlock" language (S58 addendum already called this out as wrong). Add a memory documenting the fix. **STOP.** Do not proceed to "let's also try CSHQ / ettringite / …" — that's item 4 of the pickup list and belongs to a scoped separate session, not this diagnostic.

**4F. Everything works numerically but the portlandite trajectory doesn't match experiment.**
This is a **scoping question**, not a code bug. Do not recalibrate `A₀` or `γ` or `θ` unilaterally. Open a scoping discussion with Jeff: is the S50 calibration wrong, is the textbook induction story wrong for pure alite specifically (real pure-alite pastes may not exist in the "pure" state we're modeling — trace impurities dominate real nucleation), or is voxel resolution the ceiling? **Do not touch parameters until the scoping discussion converges.**

---

## Success criteria

Verified: at the S57 pure-alite JMAK-CH config, Portlandite CNT/JMAK produces a nucleation-and-growth trajectory qualitatively reproducing the textbook induction→acceleration story (session 58 summary line 181-187): SI(Portlandite) rises above 1, seeds nucleate, seeds grow to placement threshold, voxels land, mass balance decrements aqueous [Ca] and [OH⁻] accordingly, [Ca] climbs through the story, portlandite eventually appears at experimentally plausible timing.

**Explicit non-goals** (repeated from Scope Guardrail):
1. Do NOT calibrate CNT for any other phase during this diagnosis.
2. Do NOT expand JMAK to any other phase during this diagnosis.
3. Do NOT modify voxel resolution or global timestep bounds.
4. Do NOT rewrite the CNT algorithm; only trace and, if branch 4C hits, correct the specific growth-velocity sign.
5. If diagnosis reveals a fundamental modeling gap (branch 4F), stop and open a scoping discussion.

---

## Time estimate

| Step | Wall time |
|---|---|
| 0 — Config sanity | 15–30 min |
| 1 — Paper calculation | 30 min |
| 2 — Instrumentation | 1–2 h (code + rebuild) |
| 3 — Test run | 30 min |
| 4 — Decision tree interpretation | 1–3 h depending on branch |
| **Total** | **half to full session** |

If branch 4C fires and requires a fix, add another 1–2 h for the fix + rebuild + confirmation rerun. If branch 4F fires, this diagnostic ends there and hands off to a scoping session.

---

## References

- Trace narrative: session 60 conversation (2026-08-23), Explore agent output on CNT dispatch and placement code paths.
- CNT design decisions: `docs/CNT_DESIGN_DECISIONS.md` (calibrated portlandite defaults, A₀ history).
- CNT architecture: `docs/CNT_ARCHITECTURE.md`.
- JMAK moment decomposition: `docs/jmak_moment_decomposition.pdf`.
- SaturatingRate rate law: `docs/SATURATING_RATE.md`.
- Session 58 addendum on the "pure-alite portlandite deadlock" mis-characterization: `docs/session58_summary.md:171-217`.
- Scope discipline guardrail: `~/.claude/projects/-Users-jwbullard-Code-THAMES/memory/feedback_thames_scope_discipline.md`.

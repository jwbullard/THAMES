# Transport-Controlled Kinetics — Brainstorm Conversation

**Date:** June 12, 2026
**Context:** Sounding-board conversation between Jeff and Claude (Opus 4.7). Jeff opened a new model-improvement thread (NOT UI work) addressing the limitation that THAMES cannot currently model mass-transport-controlled kinetics. No code was changed in this session — this is purely a research-direction brainstorm. Timeline is on the order of months, not weeks.

Captured verbatim for resumption in a future session.

---

## Session opening — Jeff

> I don't have a lot of time for this session, but I wanted to start up a new idea with you for improving the THAMES model (not the UI). At this point I just want you to be an honest, unbiased sounding board for some ideas I have for addressing a significant limitation of the model. Please get a good overview of the THAMES C++ code and what it is modeling if you don't already have that information.

---

## Claude — THAMES C++ architecture summary

After scanning `backend/thames-hydration/src/thameslib/`:

**Architecture (high-level):**
- **Controller** (~3.1k LOC) drives the time loop. Each cycle: kinetics compute DC upper limits → GEMS3K minimizes G under those bounds → lattice updates voxels to match the new phase budget → new SI/surface areas feed the next kinetic step.
- **ChemicalSystem** (~5k LOC + 6.9k hdr) wraps GEMS3K, holds IC/DC/phase state, suppression and IC depletion recovery.
- **Lattice** (~8.4k LOC, largest module) carries the 3D voxel microstructure, interfaces, and the growth/dissolution heuristics.
- **KineticController + four models**: Standard (`R = k A (1−Ω^p)^q`), Parrot-Killoh (clinker empirical), Pozzolanic (SCMs), Thermodynamic (no rate constraint, GEMS picks freely).
- **AdaptiveTimeController** for dt management.
- **ElasticModel / AppliedStrain / ThermalStrain** for post-hoc micromechanical homogenization.

**Implicit physical assumptions I'd call out as limitations going in:**
- Single, well-mixed bulk electrolyte — no spatial pore solution, no ion transport between connected pores, no percolation.
- Sealed/isothermal — no external water, CO₂, or temperature evolution.
- Voxel updates driven by interface lists + surface-area accounting, not by a true reaction-diffusion field.
- Coupling is one-way per cycle: chemistry decides the phase budget, lattice obeys. No mechanical feedback into chemistry (capillary stress, microcracking).
- The recent stalls we've fought (lattice-encapsulated remnants, silica-fume Portlandite oscillation) are both symptoms of this single-bulk-pore + interface-only assumption.

What's the idea?

---

## Jeff — the limitation in detail

> Excellent summary. The limitation I want to address is that THAMES cannot currently include the possibility that mass tranposrt controls the kinetics of any of the phase transformations that are being modeled. THAMES instead must assume that the electrolyte solution achieves internal equilibrium (no gradients) on time scales that are very fast copared to other kinetic processes like dissolution and precipitation of solids. This may not be a very bad approximation at early times. But eventually dissolving phases can become covered by a semipermeable layer of solic products of precipitation. When that happens, the physical reality is that a concentration gradient can develop through that layer between the dissolving phase and the electroyte. In that case I think that THAMES would not be faithfully capturing the kinetics of the reactions. I have thought of a couple of high-level approaches for trying to address that, but those ideas are not well formed. I need you to evaluate those ideas in the context of how THAMES works, let me know (honestly) if either of them could be viable and, importantly, suggest any alternative ideas that I haven't considered.

---

## Claude — landscape framing, before hearing Jeff's ideas

You've put your finger on the right limitation. The "well-mixed electrolyte" assumption is the deepest physical compromise in THAMES; everything else (single dt, single SI per phase, lattice-only product placement) sits on top of it. The lattice-trap stall and the silica-fume/Portlandite oscillation we fought recently are both symptoms — the first because a buried remnant should be cut off by transport but isn't, the second because the kinetic constraint can't damp a chemistry that needs a *spatial* gradient to relax.

Before I evaluate your two ideas, share them — they may not map cleanly onto the canonical levers, and I don't want to second-guess. To frame the landscape briefly so you can position them:

Roughly, the field has used four levers of increasing rigor / cost:

1. **Empirical rate correction.** Multiply `R = k A (1−Ω^p)^q` by `f(DOR)` or `f(δ_shell)`. This is what Parrot-Killoh's "diffusion stage" already does. Cheap, drop-in, but it's still a single bulk Ω — the gradient is fictional.
2. **Per-phase or per-voxel shell state variable.** Carry `δ(t)` for each dissolving phase, compute a steady-state diffusion flux through `δ`, derive `Ω_local` from it, and feed `Ω_local` into the rate law. Mid-complexity. The lattice neighborhood (count of product-phase neighbors per dissolving voxel) gives you `δ` for free.
3. **Two-pool electrolyte.** "Shell pore solution" vs. "bulk pore solution," coupled by a rate-limited exchange. GEMS equilibrates the bulk; the shell drifts off it according to local dissolution flux. Introduces a gradient without paying for a field solver.
4. **Reactive transport.** Concentration field per IC on the lattice; sparse diffusion solve each cycle; GEMS per cluster (or per voxel) instead of globally. Most rigorous, most disruptive — your IC depletion recovery, charge balance, suppression machinery all get rebuilt around a vector instead of a scalar.

Each of these lands in a different part of the code: (1) inside the kinetic models, (2) splits between the kinetic models and the Lattice interface tracker, (3) inside ChemicalSystem, (4) restructures Controller/ChemicalSystem/Lattice together.

What are your two ideas?

---

## Jeff — three ideas

> My first idea is a kind of spatial decomposition of the microstructure, dividing the RVE into a number of subvolumes. The GEMS3K library can calculate local equilibria and driving forces within those subvolumes and then one could add another step in the algorithm to simulate mass transport between the subvolumes. The second idea is to query the microstructure to calculate the average thickness and permeability of any precipitated layers on surfaces and then use a steady state diffuction approximation to calculate the flux within that layer, assuming that the phases on either side of the layer are near equilibrium. Under that second idea, one would need to calculate both the rate of unmodified dissolution and the rate of diffusion and choose the slowest one as the rate-controlling step.  A third idea could be to implement some kind of full-blown 3D reaction transport approach. In fact I have another model called HydratiCA that does just that, but it is *extremely* numerically intensive and I would not like to compromise the nice speed of THAMES any more than necessary.

---

## Claude — full evaluation of the three ideas + alternatives + recommendation

Quick verdicts first, then details.

**Idea 1 — subvolume decomposition:** Viable, but solves a different problem than the one you described. Won't fix the shell limitation.

**Idea 2 — shell thickness + steady-state diffusion in series:** Right tool for the right job. This is where I'd start.

**Idea 3 — full reactive transport:** You're correct to reject it for THAMES. If you wanted RT, you already have HydratiCA. Cross-validation between THAMES-with-shell and HydratiCA would be far more valuable than rebuilding HydratiCA inside THAMES.

---

### Idea 1 — subvolumes

What it actually buys you: macroscopic gradients. Aggregate ITZ, paste-to-air boundary during drying, ion ingress in leaching, carbonation depth. Real and useful problems — but **not the shell problem you described.** A product layer on a C₃S grain is sub-micron thick. A subvolume is at minimum tens of voxels per side. The gradient that limits the reaction lives *inside* one subvolume, not between two.

Cost is the bigger issue. GEMS is already the dominant per-cycle cost. N subvolumes ⇒ ~N× GEMS calls per cycle. With 64 subvolumes (4×4×4) you've turned THAMES into something an order of magnitude slower than today and you still haven't resolved the shell. And the bookkeeping is non-trivial: lattice interfaces don't align with subvolume faces, IC mass balance has to be re-derived per subvolume, charge balance has to be enforced separately in each, and you have a fresh operator-splitting error every cycle. The IC depletion / electrolyte safety machinery would need re-engineering.

Verdict: park it. If macroscopic gradient problems become a priority later (ITZ at the concrete scale, or carbonation modeling), revisit it then — but don't try to solve the shell problem with it.

### Idea 2 — shell thickness + steady-state series resistance

Right physics for the regime that's giving you trouble. A few honest caveats:

1. **"Take the slowest" is brittle; use series resistances instead.** The textbook form is
   ```
   1/R_eff = 1/R_kinetic + 1/R_diffusion
   ```
   where `R_kinetic = k A (1 − Ω^p)^q` at bulk Ω (what you compute today) and `R_diffusion = D_eff · A · ΔC_max / δ`. A hard `min()` introduces a kink — the adaptive time stepper will hate it. The harmonic mean is smooth and recovers both asymptotes correctly.

2. **"Average shell thickness" loses information.** Flux is parallel-resistor across surface voxels; a thin patch dominates. Use the harmonic mean of δ across surface sites, not arithmetic. Free to compute, large physical difference.

3. **Which species controls?** Single-limiting-IC (Ca²⁺ for clinker, SO₄²⁻ for sulfate phases, etc.) is the right start. Full multi-component flux with electroneutrality is the rigorous step; defer it.

4. **D_eff per phase pair is empirical and contested.** You'll need a small library — `D_eff(C-S-H), D_eff(AFm), D_eff(calcite shell), D_eff(ASR gel)…`. Treat it the same way you treat `k` in the Standard model: parameter to calibrate. Defensible and standard practice.

5. **Lattice can compute δ for free.** For each surface voxel of a dissolving phase, walk normal-ish through product neighbors to the nearest pore-water voxel. Bucket by particle (or just average per phase) and compute the harmonic mean. O(surface voxels) per cycle. Lives naturally in the `Interface` / `Lattice` module.

6. **What it does NOT fix: lattice trapping.** When the encapsulated ettringite remnant has zero exposed surface area, A=0, and no rate correction is going to dissolve it. You need a separate topological rule (Idea E below). This is important because you'll otherwise still hit the Session-47 stall pattern.

7. **Steady-state is a fine approximation for late ages** (the regime where this matters). Early on, shells form fast and the QSS assumption is shakier — but during that phase, dissolution dominates anyway, and the diffusion resistance is small, so the kinetic term in the series wins. The model degrades gracefully in the regime where it's least valid.

Implementation footprint: changes localized to the kinetic models (consume δ, apply series resistance) and `Lattice.cc` (compute and expose δ per phase). Doesn't touch ChemicalSystem, GEMS coupling, charge balance, or the adaptive controller. **Preserves the speed advantage entirely** — no new GEMS calls.

### Idea 3 — full reactive transport

You've stated the case correctly. THAMES's value proposition is "minutes to days, not days to weeks." Don't burn that. HydratiCA exists; if a problem truly needs RT, that's the tool. Worth keeping in mind for *validation*: run a small system in both, check that THAMES-with-shell reproduces HydratiCA's late-age behavior to within a tolerance. That's a paper.

---

### Alternatives I'd add to your list

**A. Effective-surface-area correction (cheaper than 2, often sufficient).** Don't change Ω — change A. `A_eff = A_total · g(δ)` where `g(δ)` is a sigmoid or exponential decay. Captures the shell occlusion effect without solving a diffusion equation. Drop-in to every kinetic model. Could even *replace* Idea 2 if your real problem is just that thick shells slow things down; could *complement* Idea 2 if you want both effects.

**B. Particle-population-level shrinking core.** Right now kinetics are per-phase. Going to per-particle-radius-bin (a discretization of the PSD) lets the small particles fully react while large ones still have intact cores. PK already does this for clinker via the initial particle size distribution; extend it to SCMs and reactive products. More natural than averaging δ over a phase. Requires the lattice to track particle identity, not just phase identity — a real lift.

**C. Lattice-trap detector.** Per cycle: if a phase's voxel count > 0 but exposed surface area / total surface area < threshold, flag as trapped. Then either (i) virtually dissolve the trapped voxels at a diffusion-limited rate calibrated by shell thickness, returning mass to ICs, or (ii) widen the "exposed" definition to include voxels within a diffusion length of the pore. This is the targeted fix for the Session-47 stall pattern. Worth doing regardless of which broader idea you pick.

**D. Sub-voxel shell state at the interface.** Each interface voxel carries an attribute δ that tracks shell thickness in physical units, separate from voxel resolution. Lattice stays coarse; shell is resolved as a per-site scalar. Cleaner than reading δ off lattice topology each cycle, and lets shells be sub-voxel-thin (which they usually are early on). Mid-complexity; closest to a "first-class" shell representation.

**E. Multi-component flux with electroneutrality.** The rigorous version of Idea 2 — Nernst-Planck across the shell instead of single-species Fick. Couples all ICs through the electric potential. Probably overkill for a first pass; mention it in the manuscript as the next step.

---

### My recommendation

Sequence:

1. **Ship the lattice-trap detector (C) first.** It's small, it directly fixes a stall pattern you're already hitting, and it's a no-regret precondition for the shell model — without it, Idea 2 will leave you with the same trap.

2. **Idea 2 with series resistance and harmonic-mean δ from lattice topology**, single-limiting-species per phase, calibrated `D_eff` library. This is the headline contribution.

3. **(A) as a sanity-check / lower-bound** — implement it first as a one-day exercise and see how much of the late-age stall it already removes. If it removes most of it, you have a much simpler model for everyday use and Idea 2 becomes the "high-fidelity" mode.

4. **(D) only if (2) needs a cleaner shell representation than topology can give you.** Probably don't need it for a v1.

Treat Idea 1 as a future direction for a different class of problems. Treat Idea 3 as the validation oracle, not as a path inside THAMES.

What does your timeline look like — are you scoping a paper, a grant aim, or a near-term THAMES feature?

---

## Jeff — wrap

> I have a timeline of several months if necessary, so let's not worry about that right now. However, I do need to end this session. Could you please record verbatim the conversation we just had in this session into a markdown file so you can consult it in the next session. If other memories need to be recorded, that's fine but I really want to capture the full details of everything we talked about during this session.

---

## State at end of session

- Three ideas raised (subvolume, shell + steady-state diffusion, full RT).
- Two more raised by Claude as serious alternatives (A: effective-surface-area correction; D: sub-voxel shell state at interface).
- One pre-condition raised (C: lattice-trap detector — addresses the Session-47 encapsulated-remnant stall pattern independently of the shell model).
- Two deferred (B: per-particle-radius-bin shrinking core; E: Nernst-Planck across the shell).
- Recommended path: C first → A as quick sanity check → Idea 2 as the headline → D only if Idea 2's topology-derived δ is too noisy.
- HydratiCA framed as the validation oracle, not as something to clone inside THAMES.
- Timeline: months, not weeks. Open question of paper / grant aim / feature — Jeff has not yet declared, and Claude asked.

## Open items for next session

1. Jeff to declare the scoping target (paper aim, grant aim, THAMES feature, all of the above).
2. Decide whether to start with the lattice-trap detector (C) as a standalone POST_ALPHA_TODOS item, or bundle it into the shell-model design from the start.
3. Sketch the D_eff library — which phase pairs need values, and where the literature numbers come from.
4. Identify the limiting IC per dissolving phase (Ca²⁺ for clinker is obvious; less so for SCMs and AFm-family).
5. Decide harmonic-mean-δ vs. sub-voxel-δ for v1 (topology vs. first-class shell representation).
6. Plan the HydratiCA cross-validation case — small system, late-age regime, what to compare.

## Pointers

- `docs/POST_ALPHA_TODOS.md` already contains the lattice-encapsulated-remnant entry from Session 47 — that's the empirical motivation for Idea C and a real symptom of the broader transport-controlled-kinetics gap. Worth re-reading at the start of the next session.
- `docs/session46_summary.md` documents the silica-fume Portlandite oscillation — the OTHER current symptom of the well-mixed-electrolyte assumption.
- THAMES kinetic models in `backend/thames-hydration/src/thameslib/`: `StandardKineticModel.cc` (436 LOC), `ParrotKillohModel.cc` (489), `PozzolanicModel.cc` (607), `KineticController.cc` (1580). These are where Idea 2 / Idea A would land.
- `Lattice.cc` (8406 LOC) and `Interface.cc` (139) are where δ-computation and the lattice-trap detector would live.
- HydratiCA is Jeff's separate reactive-transport model; not in this repo. Path TBD when validation work starts.

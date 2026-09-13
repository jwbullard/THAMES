# Session 65 — 2026-09-12

**Focus.** Two-week gap since S64. Reviewed the alpha-3 release-notes draft, corrected the transport-kinetics claim, deep-dived on the C_eq / shell-diffusion physics (including a self-correction of an earlier stale framing), knocked out the transport code-doc drift, added a proper reference doc, filed a long-duration validation TODO, and captured the science TODO synopsis as a continuity memory.

**Commits.** Two: submodule `f795965` (transport code-doc cleanup, pushed) + super-repo wrap-up commit (this session, includes SHELL_DIFFUSION.md, POST_ALPHA additions, release-notes softening, submodule pointer bump, session summary, CLAUDE.md history).

---

## Where we started

- On mac. Working tree clean. `main` at `60d0b9cc` (S64 wrap-up).
- Jeff came in cold after ~2 weeks; asked for a briefing on where things stand.
- Ship-blockers for alpha-3 still queued from S64: Windows verification of the aggregate-combo default, the connectivity-calculator fix, the hydration-product defaults diff, plus the Windows glass-phase auto-inject investigation (S59 residual, still open).

## Work stream 1 — Alpha-3 release-notes review

Jeff read `release-notes-alpha-3.md` and flagged the transport-kinetics claim ("Transport-controlled kinetics correction — opt-in per phase") as overstated: he didn't realize the framework was actually wired per-phase. Confirmed by grep against the code (`transport_.has_value()` gate in three kinetic models), then walked through:

- What "per-phase" means concretely (each model instance owns its own `std::optional<TransportParameters>`; call-site guard skips the correction unless the phase's JSON declared a `transport` block).
- The empirical S55 "throttle is marginal at 1 d" observation and why it looked like the framework wasn't doing anything useful.

Jeff then explained the long-standing controversy in cement science about when diffusion-controlled kinetics matters (Camp A: at or before the main heat-flow peak, 12 h or less; Camp B: JMAK space-filling dominates through the peak, diffusion doesn't matter for a day or more). His position: THAMES should stay neutral — diffusion should throttle naturally when shells thicken, not via a hand-coded time gate.

**Softened the release-notes entry** to "Transport-controlled kinetics — framework wired, not enabled for production," naming both scientific camps neutrally and acknowledging the two empirical limits (sub-voxel shell thickness at early ages; C_eq definition question).

**Wrote first draft of `project_transport_kinetics_science_position.md`** capturing Jeff's neutral stance.

## Work stream 2 — The C_eq deep dive (and a self-correction)

Jeff asked me to remind him of the C_eq issue. My first pass framed it as a formulation error — I claimed `C_eq = C_bulk / S^(1/stoich)` gave unphysical values (~10¹⁴ mol/m³ for Alite) because "S(reactant) says nothing about the concentration the diffusing ion is trying to reach on the far side of the shell." Proposed the correct C_eq should come from a "reference sink phase" (Portlandite for Ca²⁺, ettringite/AFm for SO₄²⁻).

Jeff pushed back with three clarifying questions:

1. **Damköhler reference?** Provided: original 1936 Damköhler paper, Levenspiel Ch. 25, Steefel & Lasaga 1994, Lichtner 1996, Bullard 2007, Nicoleau & Nonat 2016.
2. **Sink-phase interpretation?** Yes essentially — but this made me realize GEMS already computes C_bulk with sink-phase buffering by construction (well-mixed electrolyte + all phases at equilibrium). The "sink-derived C_eq" I had proposed was actually just the reactant-equilibrium concentration by a different name.
3. **Isn't C_surf → C_eq the whole point in the diffusion-controlled limit?** Yes exactly — and confirmed by reading `TransportCorrection.h` more carefully: the closed-form `factor = 1/(1+Da)` is derived from `k·(1 − C_surf/C_eq) = D·(C_surf − C_bulk)/δ` with C_eq being the reactant's own equilibrium concentration. My earlier "C_eq misidentified" claim was itself wrong.

Then Jeff asked the killer basic question: "In the absence of any precipitation reactions to confuse things, what would be C_eq for alite with the current value we are using for its K?"

Direct computation from `K = [Ca²⁺]³ · [H₄SiO₄] · [OH⁻]⁶ = exp(−50.7)` with stoichiometric 3:1:6 ratios gives:
- Extent of reaction `x ≈ 1.54 mM`
- `[Ca²⁺] ≈ 4.6 mM`, `[H₄SiO₄] ≈ 1.5 mM`, `[OH⁻] ≈ 9.2 mM` (pH ≈ 12)

**Completely physical numbers.** My "10¹⁴ mol/m³" figure was based on the *pre*-S56 K value where `S(Alite) ≈ 10⁻¹⁴`. Post-S56 correction, S(Alite) ≈ 10⁻³ in a real paste, and C_eq comes out in the mM–hundreds-of-mM range. The framework is physically correct; I was carrying stale pre-K-fix numbers in my mental model.

**Corrected the memory** (now titled "transport-kinetics-emergent-throttling-not-time-gate" with an explicit callout that the earlier draft's C_eq claim was wrong).

## Work stream 3 — Doc drift cleanup + reference doc

Assessed the state of documentation in the transport code: B/B+ for the file-level headers (well-annotated Doxygen), C for the surrounding ecosystem (stale "Phase 1/2/3" labels scattered across 8 files, `solveSurfaceConcentration` looked live but was never called, SR's call site pointed at Standard's derivation which didn't exist, no standalone reference doc). Jeff approved knocking it out.

**Landed in the submodule** (commit `f795965`, pushed):

- Removed 100% of stale "Phase 1/2/3" labels across `TransportStats.h`, `TransportCorrection.{h,cc}`, `TransportParameters.h`, `{Standard,SaturatingRate,Pozzolanic}KineticModel.{h,cc}`, and `KineticController.{h,cc}`.
- Rewrote `TransportCorrection.h` file docstring to state the actual current status of each function (production path vs. implemented-but-unused vs. deferred stub).
- Added the full `factor = 1/(1+Da)` derivation math to `shellCorrectionFactor`'s docstring, to `StandardKineticModel.cc`'s call-site block, and to the new reference doc.
- Added a C_eq / K-correction caveat that will prevent future readers (or model instances) from re-litigating the confusion I got stuck in this session.
- Added a dilute-solution assumption caveat on `TransportParameters::stoich`.
- Marked `solveSurfaceConcentration` explicitly as NOT CURRENTLY WIRED.
- Fixed SR's and Pozz's call-site pointers to Standard's real derivation (they previously pointed at a spot with no derivation).
- Comment/docstring only; zero behavior changes. 12 files, 194 insertions, 93 deletions.

**Created `docs/SHELL_DIFFUSION.md`** matching the pattern of `docs/SATURATING_RATE.md` and `docs/CNT_ARCHITECTURE.md`: 7 sections covering file responsibilities, JSON schema, derivation, C_eq caveat, landed-vs-deferred, verification status, references (Damköhler 1936, Levenspiel, Steefel-Lasaga, Lichtner, Bullard 2007, Nicoleau-Nonat 2016).

## Work stream 4 — POST_ALPHA additions and science-TODO synopsis

**Filed POST_ALPHA entry:** "Shell-diffusion long-duration validation run" — realistic Portland paste at 100³+, 28d–90d, Alite with transport block, watch emergent throttling grow with shell thickness. Setup sketch, success criteria, what-we-learn-if-it-fails, refinements-worth-first (nonlinear Brent, dynamic limiting-DC selection). This is the empirical anchor needed before defensibly enabling transport for a production phase in a future release.

**Delivered a five-group science-TODO synopsis** at Jeff's request. Groups: (1) shell-diffusion refinements + long-duration validation, (2) ln K audit continuation (C2S, C4AF blocked on calibration; C3A T-varying deferred; H0 audit + C3S enthalpy tracking), (3) kinetic-model coverage (JMAK-CSHQ for [Si] decay is natural next; JMAK-Portlandite production wire-up; pure-C3S CH bootstrap deadlock; CNT portlandite zero-placement), (4) K-correction consequences (C3A / C2S / C4AF PK→SR migrations blocked on calibration papers), (5) long-horizon transport research.

Recommended sequence going into next session: Windows follow-ups first for alpha-3, then JMAK-CSHQ as the science entry point (small-scope, Garrault-Nonat validation data in hand, structurally identical to landed JMAK-Portlandite).

**Captured the whole synopsis as memory** `project_science_todos_snapshot_s65.md` so a cold restart at start of next session can pull it up on request.

---

## Memory updates

- **`project_transport_kinetics_science_position.md`** — rewritten twice this session. First draft (early): "do not commit THAMES to a diffusion-onset position" with a "C_eq misidentified" claim. Second draft (after the C_eq computation exposed the error): "C_eq formulation is physically sensible post-K-correction; earlier claim was WRONG"; two refinements worth doing but not blockers.
- **`project_science_todos_snapshot_s65.md`** — new, containing the full five-group science synopsis + Windows-first-then-JMAK-CSHQ recommendation. Designed to be the answer when Jeff asks "where do we stand on the science?" in a future session.
- **MEMORY.md index** — updated both memory pointer lines.

---

## Working-tree state at wrap-up

Super-repo:
```
 M .claude/settings.local.json  (harness state; incidental)
 M CLAUDE.md                    (S65 history entry)
 M backend/thames-hydration     (pointer bump 6f40f4a → f795965)
 M docs/POST_ALPHA_TODOS.md     (shell-diffusion validation entry)
 M release-notes-alpha-3.md    (transport-kinetics entry softened)
?? docs/SHELL_DIFFUSION.md      (new reference doc)
?? docs/session65_summary.md    (this file)
```

Submodule at `f795965` (pushed). Super-repo commit to follow as post-session sync.

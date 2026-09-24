# Session 72 Summary (Sep 23–24, 2026): pore volume separated from wetting weight; percolation groundwork

Continuation of the same working session as S71 (the alpha-3.1 emergency), after that release shipped. All work here is backend C++ plus one small UI-service change. Entry point for the next session: memory `project_volume_accounting_handoff.md` and `project_percolation_and_cavities_design.md`.

## The problem C1/C2 fixed

`microPhasePorosity_` answered two unrelated questions with one number: how much pore volume a phase contains, and how strongly a voxel wets its neighbours (the `wmc` weight behind dissolution and growth eligibility). VOID needs opposite answers — it is entirely pore space, yet must wet nothing — so it carried 0, and the pore size distribution became blind to empty capillary voxels. The CSV reported `Empty voxel-scale void volume fraction = 0` while `Microstructure.csv` simultaneously showed several percent VOID, and `getLargestSaturatedPore` never saw those pores, so Kelvin RH read exactly 1.0 while capillary pores stood empty.

Jeff rejected the proposed local workaround (step B) in favour of the principled separation, conditional on it not being large or risky. A scope check justified that: of 99 references, only **three** are pore-volume semantics; ~22 are wetting weights; the rest are plumbing. VOID and ELECTROLYTE are excluded by loop bounds from two of the three volume sites, so only the pore-size path changes behavior.

## Landed

- **C1 (submodule `fe2ed57`)** — new `microPhasePoreVolumeFraction_` (+ integer companion): VOID = 1, ELECTROLYTE = 1, solids = sub-voxel porosity, kept in step at all five write sites including `calcMicroPhasePorosity`. The three pore-volume consumers switched to it; `getPoreVolumeFractions` now queries `ChemicalSystem` directly rather than `Lattice`'s cached copy, which a CSHQ porosity update could leave stale.
- **C2 (submodule `2e47292`)** — 119 substitutions renaming `microPhasePorosity_` → `microPhaseWettingWeight_` (+ `Int`), accessors, and `electrolyteIntPorosity_` / `voidIntPorosity_`. `calcMicroPhasePorosity` deliberately keeps its name: it computes the phase's physical porosity, which is then stored in both derived views. The declaration's docstring no longer calls the field "the sub-voxel porosity" — the phrasing that invited the original conflation.
- **D1 (submodule `a1789db`)** — `Lattice` loads the `.pimg` particle-id image into `particleId_`, with `hasParticleIds()`, `getParticleId()`, `isOriginalParticle()`. micgen writes `partid + 1` for particle voxels and ELECTROLYTE (1) elsewhere where VCCTL wrote 0, so the predicate treats `<= 1` as "no particle" and reads either convention. A missing or mismatched file is not fatal.
- **D2a (submodule `5ec807b`, super-repo `80d6b0e6`)** — per-phase `rigidity.participates` flag parsed from simparams.json (default true for solids, false for VOID/ELECTROLYTE) plus `initialMicroPhaseId_`, `bondsToNeighbors()`, and `sameOriginalParticle()`. `simparams_service.py` now emits the block with a provenance string. **No phase name appears in the C++**, at Jeff's request, so non-portland systems need no code change.

## Validation

| Test | Result |
|---|---|
| Saturated Ca11mM, C1 vs HEAD | 29/29 CSVs byte-identical |
| Saturated Ca11mM, C2 vs C1 (pure rename) | 29/29 identical |
| Saturated Ca11mM, D1 and D2a | 29/29 identical |
| Sealed cem151-neat 28 d, C1 vs A2 | empty capillary porosity now matches `Microstructure.csv` VOID to five decimals (was 0.00000 throughout); Kelvin RH 0.9979 while capillary voids coexist with capillary water (was exactly 1.0); late-age RH unchanged (0.9709 at 28 d); DOR 0.79358 vs 0.79384 (−0.03 %); H and O conserved exactly |
| `.pimg` / `.img` alignment, checked independently in Python | all 584,043 Electrolyte voxels have `pimg == 1`; all 415,957 solid voxels have `pimg > 1` (38,873 particles) |

Run directories: `~/tmp/thames-rh-validation/sealed-{A2,C1}`, `~/tmp/thames-{A2,C1,C2}-Ca11mM`, `~/tmp/thames-D1-test`, `~/tmp/thames-D1-nopimg`, `~/tmp/thames-rigidity-test`. Re-run the comparisons with `~/tmp/thames-C1C2-review.sh`. Baseline binaries: `/tmp/thames-A2-baseline`, `/tmp/thames-C1-baseline`.

## Two hypotheses of mine that the evidence killed

- I suspected `poreSizeDist[VOIDID][0]` indexed an empty vector — undefined behavior on every run. An instrumented build printed `VOID_rows=1 ELECTROLYTE_rows=1`: the synthetic rows exist. No UB.
- My first saturated regression showed 14 differing CSVs. The baseline predated A2, so those were A2's Fe(II)→Fe(III) change. A properly built baseline gave 29/29.

## Jeff's observation worth carrying forward

Sealed VOID fraction falls after 14 d (0.068 → 0.035 at 28 d) because `Lattice::nucleatePhaseRnd` (~line 2083) falls back to VOID sites once Electrolyte voxels reach zero, around 304–308 h. Late-age product therefore fills empty capillary space and the emptiness migrates into the gel pores — which is why the PoreSizeDistribution files start recording interhydrate emptying at the same moment. Physically those capillaries should stay empty and late product should densify CSHQ instead. Scheduled after the cavity work.

## Decisions recorded for the remaining work

Captured in memory `project_percolation_and_cavities_design.md`:

- **How pore voxels are emptied:** exact periodic Euclidean distance transform; seed at the deepest point; grow cavities adjacent to existing VOID; **nucleate a new cavity with probability 0.05 per placed void voxel**; refill symmetric (smallest distance first).
- **Set definitions:** initial set = 3D rigidity percolation, first connectivity in all three directions; final set = connected fraction 0.985, held in a named constant that is easy to change but not user-editable.
- **Capillary porosity for `burn3d`** = VOID + ELECTROLYTE.
- **Outputs:** both a pair of binary columns appended to `Microstructure.csv` and a separate small CSV of setting category vs time, plus the connected fractions over time.
- **Schedule:** solids + electrolyte every 10 min of hydration time until initial set; capillary pores every 1–2 h after.

## Next

**D2b — the percolation core.** `Percolation.h/.cc`: one labeling pass over a caller-supplied participation predicate and the contact rule, per-direction non-periodic spanning tests (periodic-merged labels only for cluster statistics), returning spanning flags plus connected fraction. Unit tests on synthetic lattices: a bar spanning one axis, two touching grains that must not connect, and a seam-wrapping cluster that must not falsely percolate. Then D3 (schedule + outputs), the depercolation-to-sealed switch, the cavity work, and late-age densification.

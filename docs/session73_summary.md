# Session 73 (Sep 25–28, 2026): percolation wired up, sealed-mode emptying rebuilt, shrinkage and humidity outputs

Continuation of the sealed-mode thread from S72. Everything below is pushed:
submodule `5ec807b..331513d` (six commits), super-repo `c5cbfcbc..21f039bc`
(three pointer bumps).

---

## 1. Percolation core and wire-up (D2b, D3)

`Percolation.h/.cc`, `namespace percolation`, no THAMES dependencies.
`assess(nx, ny, nz, participates, bonds, particleId)` returns per-axis
`{spans, numSpanningVoxels, connectedFraction}` plus `spansAllDirections()` and
`minConnectedFraction()`. **Three labeling passes, one per axis**, each with
that axis non-periodic and the other two periodic — not one pass followed by a
spanning test, which is the S64 bug. Unit tests in
`src/unit_tests/test_percolation.cc`, 22 assertions.

`Lattice::assessRigidityPercolation()` / `assessCapillaryPercolation()` build the
arrays; `Controller` owns cadence and set state, assessing only on the
successful-cycle path because a GEMS-rejected cycle is retried from the same
state.

Outputs: `InitialSet`/`FinalSet` columns on `Microstructure.csv`, written
**empty rather than 0** when there is no `.pimg`, so "we did not look" is never
read as "it had not set"; `<job>_SettingTimes.csv`; `<job>_Percolation.csv`.

**`FINAL_SET_CONNECTED_FRACTION = 0.80` is PROVISIONAL.** VCCTL's 0.985 put
final set at 19 h against an initial set of 2.55 h. 0.80 is the connected
fraction this paste reaches at 5 h. Wants Vicat calibration across several w/c.

**Cadence settled at 10 min until FINAL set, 2 h after** (revised from initial
set mid-session). Switching at initial set had pinned final set to the hour it
fell in — 5.618 h was simply the first hourly assessment past the crossing; the
real crossing is 4.895 h. The gate is `setDetectionAvailable_ && !finalSetDetected_`,
so a run with no particle-id image uses the coarse interval from the start.
Observed spacing in the setting window is 0.18–0.22 h, so the timestep and not
the schedule is the real limit there.

Bug fixed en route: percolation state was initialized at the top of the
`Controller` constructor, dereferencing `lattice_` 80 lines before it is
assigned. First run segfaulted in under a second.

## 2. Saturated → sealed switch on capillary depercolation

When capillary porosity stops spanning in **all three directions**,
`chemSys_->setIsSaturated(false)`, one-way.

**Jeff's argument for the criterion is better than the one first written down
and is now what the code records.** Under periodic boundaries the RVE has no
surfaces — it is an embedded volume in an unbounded body — so a cluster
touching a face simply continues into the adjacent image. Only a *spanning*
cluster forms an unbounded path that can reach a real surface. Spanning is
therefore not a conservative proxy for surface access; it is the only statement
available. This also puts capillary depercolation on the same footing as set
detection, which has always been spanning-based.

Validation (saturated cem151-neat, 28 d): fires at 49.93 h; all 20 time-series
CSVs identical to the unswitched run up to that point; VOID exactly 0 before and
first appears at the next output time; DOR 0.79621 against 0.79671 always-saturated
and 0.79358 sealed-from-start; zero `adjustMicrostructureVolumes` volume errors,
which is the check that the saturated-mode assertion really stood down.

## 3. How pore voxels are emptied

**EDT replaces the 7³ window.** `DistanceTransform.h/.cc`, `namespace edt`,
exact Felzenszwalb–Huttenlocher, periodic by transforming each row tiled three
times and keeping the middle copy, 57 ms at 100³. The old rule counted like
voxels in a box, which saturates: a voxel deep in a large pore and one in a
modest pore both scored 343. Deleted `findDomainSizeDistribution` (now unused)
and `findDomainSize` (already dead).

**The cavity nucleation probability was deleted, not retuned.** Jeff proposed
putting void nucleation on a CNT footing. Worked through, the numbers rule it
out: at the Kelvin RH of 0.97 this paste reaches, the tension is ~4 MPa against
RT/V_m = 137 MPa, giving r\* = 36 nm and **W\*/kT ≈ 9×10⁴**. Homogeneous
cavitation of water needs ~150 MPa. Heterogeneous does not help — the shape
factor for a *vapour* nucleus is set by the contact angle measured through the
vapour, so bubbles are catalysed by hydrophobic surfaces, and cement hydrates
are hydrophilic. Experiment agrees: confined water in mesopores cavitates only
below RH ≈ 0.4.

So vapour is not created inside the specimen; it arrives from an air void along
the capillary network. **Jeff's observation settled where those voids are:**
entrained and entrapped air is >100 µm, larger than the whole 100 µm box, so a
typical RVE contains none and the front enters from outside. One invasion
front, with nucleation surviving only as the fallback for a pore cluster that
cannot be reached at all. Parameter-free.

7 d, sealed reference: **1711 void clusters → 10**, singletons 0.8 % → 0 % of
void volume, largest cluster 5,425 → 63,851 voxels holding 95.6 %. Clusters are
**ramified, not spherical** (R_g/R_sphere 1.2–2.4) — invasion percolation
following the coarse pore network. An earlier comment claiming "roughly
spherical" was wrong and was corrected.

Capillary depercolation consequently moves 76 h → 484 h: one connected vapour
network *is* connected capillary porosity, where 1711 fragments are not. The
saturated→sealed switch keys off this.

Cost: first implementation was ~40 % slower. Profiling (not guessing — an
earlier throughput comparison at different simulated times was invalid) showed
the EDT was only half of it; the rest was a `callRNG()` per lattice site and a
full sort of ~500 k candidates per call. Now a heap built in one pass, and ties
broken by hashing the site id against a per-call seed. Final cost +5 %.

## 4. Chemical and autogenous shrinkage, and the humidities

Jeff's suggestion, both with ASTM methods behind them.

`<job>_Shrinkage.csv`. **Chemical shrinkage is trustworthy**: from
`getGEMVolume()` (all non-gas phases, m³ per 100 g solid) minus a new
`cumulativeWaterImbibed_`, since matter entering from outside is not reaction
product. **0.0569 mL/g solid and 7.5 vol% at 28 d**, against 0.06–0.07 mL/g in
the literature at full hydration with DOR 0.79, and against the 7.7 % measured
independently in S70. Same quantity in sealed and saturated mode, which is what
C1608 weighs.

**Autogenous strain is a framework only — about 10× low, do not quote it.**
Biot–Bishop, `eps = -(S σ_cap/3)(1/K - 1/K_s)`, with both moduli from a new
self-consistent homogenization evaluated with every pore empty (drained means
the fluid carries no load). Reasons for the gap, in order: the estimate is
elastic and measured shrinkage is substantially viscoelastic; tension is low
and quantized; K_s comes out 21.7 GPa where a C-S-H/CH/clinker skeleton should
be nearer 30–50, which is worth auditing in `elasticModuli_`. Inputs are
written beside the strain so it can be recomputed under a different treatment
without rerunning.

**No final-set-referenced column, though C1698 measures from there.** The
self-consistent scheme has no usable stiffness until 10 h while final set is
4.4 h, and a datum taken at the 1 GPa floor sits where 1/K is most inflated —
subtracting it turned a contraction into an apparent +800 µε of *expansion*.

`Homogenization.h/.cc`, `namespace homog`. Jeff chose self-consistent over
Mori–Tanaka after the trade-offs were laid out: MT is explicit, coincides with
a Hashin–Shtrikman bound for well-ordered two-phase composites, and is better
motivated for a *mature* paste — the literature multiscale models use SC at the
gel level and MT at the paste level. SC wins here because the window that
matters has no matrix to nominate and the natural choice would change mid-run.
Unit tests include the fact that **the scheme does not satisfy Gassmann** (pore
fluid stiffens the shear response, because each phase is an isolated
inclusion), which is exactly why the caller passes pores as empty.

Two defects found by running rather than reading: the first draft took chemical
shrinkage from `initMicroVolume_ - microVolume_` and got a *negative* answer
(`microVolume_` inflates porous solids by 1/(1-φ) and can exceed the box); and
the SC solve never reported convergence, for two compounding reasons — the
plain fixed point oscillates for many phases with spread moduli (now
under-relaxed 0.5), and convergence was measured against the *current* estimate,
so a paste walking toward zero stiffness showed 100 % change however settled
(now measured against the fixed Voigt reference).

`<job>_Humidity.csv` carries Kelvin RH, water activity, their product, meniscus
diameter and saturation by pore scale. Separated because **only the Kelvin term
puts the liquid in tension**; dissolved salts lower vapour pressure without
pulling on the skeleton. A measured internal RH is therefore not directly
comparable without dividing out the activity.

## 5. The 100 nm – 1 µm gap

The meniscus is now interpolated within its bin (log-diameter, using the bin's
own `volfracsat`) rather than snapped to the edge. Distinct meniscus diameters
16 → 107. This changes results, not just reporting, since `getKelvinRH` feeds
the rate throttle.

It helped less than predicted, and **the original diagnosis was wrong**: the
factor-of-ten tension swings are not 12 % bin quantization. The coarse end of
the distribution is a *single* bin labelled `>=1000`, holding every voxel-scale
pore, with nothing between 100 nm and 1 µm.

**A proposed EDT-based capillary PSD was investigated and rejected on
measurement.** The EDT-derived distribution runs *upward* from 1000 nm (median
exactly 1000 at every age; max 5–11 µm), because at 1 µm voxels the finest
resolvable capillary pore *is* 1000 nm. The whole capillary range implies
0.025–0.287 MPa against 3–10 MPa from gel pores, so it cannot move autogenous
shrinkage; by 28 d, 92 % of capillary volume sits at the floor and the lump is
nearly exact; kinetics would not notice (f(h) 0.9930 → 0.9988); and
`calculatePoreSizeDistribution` runs every fresh step, so a per-call EDT would
add ~50 % runtime.

**Literature search then settled the shape.** PDC-MIP on OPC paste at w/b 0.4
finds a persistently bimodal distribution — capillary peak 0.8–10 µm, second
peak 0.01–0.1 µm, surviving 28 to 370 d — and the ¹H NMR populations of Muller
& Scrivener run interlayer 1 nm, gel 3 nm, interhydrate 10 nm, then capillary
above 0.5 µm. **Both put 100 nm – 1 µm in the valley between populations**, so
Jeff's fallback of a linear distribution would have overstated it and flattened
a bimodality two independent techniques agree is real. The steep fall in
humidity there is therefore largely *physical*; only its discontinuity was ours.

`Lattice::CAPILLARY_BRIDGE_SHARE = 0.15`, uncalibrated: that share of
voxel-scale porosity is treated as lying log-uniformly over 100 nm – 1 µm, and
since draining takes coarse pores first the meniscus enters it only once the
capillary system is 85 % empty. The meniscus then walks 783 → 552 → 417 → 243 →
224 → 183 → 123 nm over 272–308 h with tension climbing 0.37 → 2.34 MPa, in
place of sitting at 1000 nm and 0.287 MPa for 40 h and then jumping. It fires on
exactly one window because a sealed run has one transition from
capillary-dominated to gel-dominated drainage — the one already noted in S72,
where electrolyte exhausts between 304 and 308 h.

**Affects the meniscus position only.** Volume and saturation were deliberately
left alone: `emptySubVoxelPorosity` walks the master distribution from the
largest bin down without checking pore scale, so bridge volume would be drained
twice — once by voxel conversion, once there.

---

## Reference facts established

- **cem151-neat is w/c = 0.443** (44.26 g water per 100 g solid; 75.49 cm³
  total; mean solid SG 3.20). That sits essentially *on* the Powers limit for
  complete sealed hydration, which is why sealed and saturated DOR differ by
  only 0.4 %. **Use w/c 0.30–0.35 to make the curing modes actually separate.**
- The RH throttle barely engages at this w/c: `h0 = 0.70` and sealed Kelvin RH
  never falls below ~0.97, so f(h) ≥ 0.90.
- At 28 d: Kelvin RH 0.9704, water activity 0.9527, internal RH 0.9245.
- `initMicroVolume_ - microVolume_` is **not** chemical shrinkage.
- A `file(GLOB ...)` CMake cache means a new `.cc` needs `cmake ..` before
  `make`, or it links with undefined symbols.
- Doxygen hazard: `4 G*/3` and `(G*/6)` contain `*/` and silently close the
  comment block. Use starless names.

## POST_ALPHA entries filed

1. Autogenous shrinkage from a fixed-volume RVE — Biot–Bishop, every input
   already exists; caveats on which RH, Bishop's S below 0.8, and creep.
2. Pore sizes between 100 nm and 1 µm are not represented — rewritten after
   measurement to record why the EDT route was rejected, what the bridge does,
   and the three remaining options.

## Next

Late-age nucleation-into-VOID moisture rule (meniscus-diameter per-phase proxy,
decided 2026-09-24). It is what re-fragments the cavities once electrolyte runs
out: 10 clusters at 7 d → 7,096 at 28 d, 70 % singletons, from solid nucleating
onto void walls at ~26,600 eligible sites box-wide. Then pre-set shrinkage,
gel-pore collapse, Kelvin adsorbed-film correction.

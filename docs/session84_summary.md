# Session 84 (Oct 19, 2026): pore populations re-examined; Allen-basis gel porosity reported

Science session on where gel densification happens and the 100 nm - 1 um
pore-size gap. No physics changed yet; one reporting column landed. Design and
inventory analysis are in memory `project_late_age_csh_pore_physics.md`.

## Sync

`./pre-session-sync.sh` ran on macOS for the first time since the LF
conversion (S83): completed, nothing to pull. Only local change was the dev
UI's window position in `config/preferences.yml` (left uncommitted).

## What the pore population is today

- Only CSHQ carries a sub-voxel pore curve (simparams `poresize_distribution`,
  0.23-99 nm). Every step it is rescaled by phi(psi) and the CSHQ volume
  (`Lattice::getPhasePoreSizeDistributions`, `Lattice.cc:5673`). Voxel-scale
  ELECTROLYTE/VOID form one bin at the voxel size.
- Histogram bins 100-1000 nm exist (`setPSDiameters`) but never receive volume.
- The curve (Jeff's reading of Naber et al. 2020, Materials 13:1779) splits
  as: 0.1-2 nm 25 % (interlayer), 2-10 nm 36 % (gel), 20-100 nm 39 %
  (interhydrate at Naber's scale).

## Literature reading (Muller 2013 JPCC 117:403; Naber 2020; Konigsberger 2016)

- Same three NMR populations in both papers; sizes differ by surface
  relaxivity: Muller 0.85 / 2.5 / 8-10 nm, Naber 0.7-1.2 / 4.9-8.1 / 33-54 nm.
  **Jeff chose Muller's scale** (C3S C-S-H differs from portland paste; SEM
  sizes carry vacuum, sampling and contrast artifacts).
- Muller: pore sizes fixed after ~0.5-1 d; gel porosity plateaus 1-2 d to
  ~60 d (LD then HD product); interhydrate pores keep their size and lose
  volume to zero by ~2 months at w/c 0.40 ("present or filled"); only then
  does C-S-H fill gel pores. Matches Konigsberger regimes II/III.
- **Konigsberger's gel = Allen solid (incl. interlayer, 1.8 H2O/Si) + NMR gel
  pores; interhydrate counts as capillary.** So THAMES phi is gel-pore
  porosity, not coarse space. My first proposal (coarse class inside CSHQ)
  was withdrawn on this ground.

## Water inventory (Jeff's question), sealed w/c 0.32, per mol Si

GEMS CSHQ solid: 2.87 H2O/Si, 2.25 g/cm3, 90.0 cm3 = ~70.6 Allen-type solid +
19.4 cm3 of water above 1.8 H2O/Si. Envelope = GEMS solid/(1 - phi) on either
basis (exact). Conclusions:

- Removing interlayer bins and moving the interhydrate tail out of the gel
  curve change **no** water inventory, envelope or voxel count: phi contains
  neither; those bins are gel-pore volume with wrong size labels.
- **Real finding:** ~1.07 H2O/Si of NMR gel water is held as GEMS solid
  (17 % of gel water at 24 h, 41 % at 28 d). Invisible to the PSD, Kelvin RH
  and GelPoreSaturation; harmless for self-desiccation (2.5 nm pores empty
  only below RH ~0.43), relevant for drying and for literature comparisons.
- Kelvin RH: 2.5 nm 0.43, 8 nm 0.77, 10 nm 0.81, 50 nm 0.96, 100 nm 0.98.
  The RH range 0.8-0.99 that matters for self-desiccation is controlled by
  interhydrate + sub-um capillary porosity, which today is mislabeled gel
  volume plus the bridge share.

## Landed: `GelPorosityAllen` column in `_CSH.csv` (submodule)

- Allen constants moved from `calcCSHPsi` to file scope (anonymous namespace,
  `ChemicalSystem.cc`); `CSHGelProperties::allenGelPorosity`;
  `getCSHGelProperties` computes phi + (n_H2O - 1.8 n_Si) V_w (1 - phi) /
  V_solid; column appended last in `Controller.cc`.
- Verified on sealed w/c 0.32 (672 h): 0.617 at 24 h, 0.397 at 672 h vs GEMS-
  basis 0.513 / 0.235; all other columns byte-identical over 446 rows.

## Design agreed for next session

1. CSHQ curve: gel pores only, log-normal near Muller's 2.5-3 nm with
   realistic width; no interlayer bins (Jeff agreed); no tail above ~10 nm.
2. Fine capillary class (interhydrate + sub-voxel capillary, ~8 nm up to the
   voxel size): carried by **hydrate voxels**, not ELECTROLYTE (electrolyte
   drains first and would leave the class without a carrier). Consequence:
   product envelopes inflate, electrolyte voxels shrink by the same volume,
   setting/depercolation move earlier; water and total pore volume unchanged.
   Check psi consistency. Volume share grows as free water becomes
   interhydrate (Muller Fig. 2, w/c 0.32/0.40/0.48, needs digitizing).
   Consumed largest-first at fixed size. Retires `CAPILLARY_BRIDGE_SHARE`.
3. Widths matter: narrow populations would crash RH from ~0.8 to ~0.45 when
   interhydrate is exhausted.
4. Resolution: the class must run exactly to h and hold the part of a
   reference capillary distribution below h (the bridge is hard-coded to
   100 nm-h at 15 %, not resolution-consistent). Validation: same mix at
   h = 0.5, 1, 2 um gives the same master PSD, RH and chemical shrinkage.
5. Proximity to clinker (inner/outer, HD/LD) stays a later step.

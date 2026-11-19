# Session 89 (Nov 19, 2026): to-do list additions; transport.c and genaggpack.c in the repo

Planning only; no code changes. Commit `8b1d0fb7` (pushed).

## UI to-dos (`docs/UI-Issues.md`, section "To-dos raised by Jeff (2026-11-19)", alpha.5)

1. Log-normal sigma default 1.0 instead of 2.0 (`unified_psd_widget.py:251, 414, 435`;
   also update alpha-4.3 Known Limitation 17).
2. Aggregate specific gravity, bulk and shear modulus as editable Mix Design fields
   stored with each mix, replacing the source dropdowns; the shape-set dropdowns stay.
   Needs new `mix_design` columns plus a migration that fills old mixes from their
   current aggregate row; Mix Design and Elastic read the mix values.
3. "Manage Grading Templates..." moved into the Grading dialog.
4. Plot Data button folded into the Results viewer (its only unique plot is the
   cement PSD).
5. Any variable as the abscissa in Data Plots (join CSVs on time; draw in time order).
6. Diffusive Transport page parallel to Elastic Moduli. Output: the formation factor.
   Jeff will supply per-phase diffusivities and their sources.

Dropped: renaming MA106A-1-fine to "Ottawa sand" (Jeff withdrew it; a separate
`Ottawa-sand` shape set already exists, and MA106A-1-fine's source is Holcim).

## New VCCTL sources in `backend/src/` (unmodified, not built)

- `transport.c` (~2000 lines): paste-scale Garboczi finite-difference CG conductivity
  (x, y, z fields), formation factor; concrete scale `conctransport()`, an EMT with
  ITZ layers (transport analog of Concelas). Adaptation as for `elastic.c`: THAMES
  phase mapping and a phase-property key instead of VCCTL ids and its built-in sigma
  table, an input file instead of stdin, CSV with provenance, a build target.
  Recommended: standalone `bin/transport`, like micgen. THAMES points: VOID sigma 0
  makes F saturation-dependent in sealed runs; CSHQ sigma could follow gel porosity.
- `genaggpack.c` (~3400 lines): random parking of real-shape aggregate; `additz()`
  makes a one-voxel ITZ shell; `connect()` tests ITZ connectivity.

## DEFERRED (research direction, long-term)

Concrete-scale properties by explicit mesostructure (genaggpack) and a second FE
calculation instead of EMT, to capture ITZ percolation. Core obstacle: resolving a
10-20 um ITZ needs ~2e10 voxels for mortar, ~2e12 for concrete. Options: thin-layer
ITZ with rescaled (anisotropic) properties, nested paste -> mortar -> concrete, size
cutoff. Jeff wants to think carefully about whether it is worth doing.

## Next

- Tutorial Ep 7 re-record and Ep 8 (sandbox `--source` is the published 4.3).
- alpha.5 after the series; Diffusive Transport needs Jeff's diffusivity table first.

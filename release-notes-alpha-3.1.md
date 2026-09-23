THAMES 1.0.0-alpha.3.1 - Release Notes
=============================================

A small patch release over 1.0.0-alpha.3, containing user-interface fixes only.
The simulation engines (micgen and the THAMES-Hydration backend) are byte-for-byte
the same binaries that shipped in alpha-3, so results from alpha-3 remain
reproducible under alpha-3.1. Upgrading in place preserves your database,
operations, and settings: they live in a separate tree
(%LOCALAPPDATA%\THAMES\ on Windows, ~/Library/Application Support/THAMES/ on
macOS) that the installer never touches.

### Fixed since alpha-3

  1. **Mix Design panel: aggregate mass with no aggregate selected.**
     Entering a mass for a fine or coarse aggregate without choosing an
     aggregate from its dropdown silently dropped that aggregate from the
     mix while still counting its mass in the total. The Validate button
     then reported the arithmetic symptom rather than the cause, e.g.
     "All component mass fractions sum to 0.526, should be 1.0" for a mix of
     0.9 kg cement + 0.1 kg limestone + 0.2 kg fine + 0.7 kg coarse aggregate.
     The panel now names the cause as soon as the mass is entered:
     "Fine aggregate has 0.2 kg but no aggregate is selected - choose one from
     the dropdown, or set its mass to 0." The same check covers a component
     row carrying a mass with no material selected.
     Workaround on alpha-3: select the aggregate in the dropdown before
     entering its mass.

  2. **Mix Design panel: "Create Mix" no longer starts a run on an invalid mix.**
     Validation was advisory only at the button, so a mix the app had already
     judged invalid could still be sent onward. Create Mix now runs the full
     validation first and refuses with a dialog listing exactly what is wrong.

  3. **Mix Design panel: low powder content is a warning, not an error.**
     A mix whose powders are under 10 % of total solids was reported as an
     error. That threshold is portland-concrete practice, not a data
     requirement, and THAMES models systems well outside it (lean mixes,
     mortars, non-portland binders). It is now a warning and no longer blocks
     generation. Mixes with genuinely broken proportions - fractions that do
     not sum to 1, duplicate materials, negative water - are still errors.

  4. **Operations panel: the microstructure progress bar no longer appears frozen.**
     micgen reports milestone progress as 1 %, 5 %, 50 %, 65 %, 95 %, 100 %,
     with nothing emitted during particle placement - the longest phase, which
     runs for minutes with real-shape particles. The display therefore sat at
     "Adding particles / 50 %" for the whole placement phase and looked hung;
     at least one working run was killed because of it. The panel now reads
     micgen's fine-grained placement progress and shows it as
     "Placing particles (N %)" climbing through the 50-65 % band.
     Note: if a microstructure run looks stalled, check the operation folder -
     a finished run writes <name>.thames.img and micgen_progress.json
     containing "percent_complete": 100.

  5. **cement_psd.csv is now written for every microstructure.**
     The routine that creates it called a VCCTL-template method that was never
     implemented in THAMES, so the file has never been produced and every
     generation logged "Error creating cement PSD file: 'MixService' object has
     no attribute 'get_current_mix'". The cement particle size distribution now
     comes from the selected material's PSD record, the same source used for
     the micgen input file. This file feeds the ITZ width calculation (taken as
     the median cement particle diameter) and the Effective Moduli panel's
     Concelas cement PSD input; both previously fell back to defaults or
     reported that the width could not be calculated. Elastic and ITZ results
     computed under alpha-3 and earlier were affected by this fallback;
     microstructure generation and hydration were not.

### Known limitations carried over from alpha-3

  All known limitations listed in the alpha-3 release notes still apply.

  In addition: a correction to water conservation in the hydration backend is
  complete but deliberately held back from this patch, because it changes
  simulation results and warrants its own validation and release notes. It will
  ship in a later release. Its practical effect on saturated runs is small
  (28-day degree of reaction was unchanged at 0.7967 in a w/c = 0.44 portland
  paste); sealed-mode runs are affected more substantially.

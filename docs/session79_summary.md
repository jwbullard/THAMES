# Session 79 (Oct 13, 2026): densification step 4, published Known Limitations, alpha-4 plan

Planned: implement and thoroughly test gel-densification step 4, then decide
whether to ship alpha-4. Step 4a (largest-first gel-pore removal) was built,
tested, and dropped; step 4b (`wmc0_` restamp) landed. Known Limitations were
added to the published alpha-3 and alpha-3.1 releases. All pushed.

Commits: submodule `af0c95f`; super-repo `6bc12300`.

## Step 4a: largest gel pores first (REVERTED)

- **Design.** When φ falls below its running maximum (running maximum chosen
  by Jeff), remove the missing pore volume from the largest rows of the CSHQ
  input curve first; also feed the truncated curve to the moisture rule and
  `GelPoreSaturation`. Gated on densification.
- **Tests (100³, 672 h, against `dbc9751`).**
  - `enabled: false`: byte-identical.
  - w/c 0.443 sealed, saturated, fly ash: only PoreSizeDistribution files
    differ.
  - Sealed w/c 0.32 and 10 % limestone changed.
- **Failure.** In the sealed limestone run the meniscus flip-flopped between
  about 2 nm (Kelvin RH 0.35, below h0 = 0.70, so all kinetics stopped) and
  1000 nm. φ falls 0.73 → 0.18, so removing about 75 % of gel-pore volume
  from the top empties the curve above about 4 nm, leaving no capacity
  between 4 and 1000 nm. Water displaced by densification refloods VOID
  voxels (meniscus 1000 nm). Hydration then consumes it, and the meniscus
  drops straight to the sub-4 nm rows. The 28-day limestone DOR was 1.5
  points low. Jeff's restatement of the mechanism was confirmed.
- **Underlying issue.** The CSHQ curve (0.23–99 nm) carries 10–100 nm
  interhydrate pores, which measured pastes keep for a year. THAMES has no
  pore population of its own; each step rebuilds sub-voxel pores from phase
  curves.
- Reverted at Jeff's request; proportional scaling stays. The patch is kept
  only in the session scratchpad.

## Step 4b: `wmc0_` restamp (submodule `af0c95f`)

- `Lattice::restampWettingWeights`, called in `changeMicrostructure` right
  after `microPhaseWettingWeightInt_` is refreshed. When any solid phase's
  weight changed, solid sites with a stale `wmc0_` are restamped; the
  difference goes to the site's own `wmc_` and to its 18 neighbors'.
- **Neutral on results.** DOR and Kelvin RH within 3e-4 in all six cases.
  Setting times moved by up to 0.35 h in both directions. Two seeds of the
  same code differ by up to 0.46 h (initial set), so this is noise.
  `THAMES_SUMTREE_CHECK=3` was clean over about 2.9 M draws.
- Seed replicas used a throwaway build with `seedRNG = -31337`
  (`thames.cc:139`); the source was restored.

## DEFERRED (two entries)

- Setting times carry about ±0.3 h of seed noise at 100³: calibrate
  `FINAL_SET_CONNECTED_FRACTION` over several seeds or at 200³; consider
  making the seed an input.
- The capillary-depercolation event is erratic in sealed runs (VOID +
  electrolyte sits near threshold; it changes nothing in sealed mode, but
  the same sensitivity could move the saturated→sealed switch).

## Physics discussion: late-age C-S-H and pores

- **Option B (after alpha-4):** a tracked sub-voxel pore population V(d)
  with sources and sinks (birth curves for new product, densification
  removing from the largest *wet* bins, dissolution adding back), in place
  of the per-step rebuild.
- **Jeff:** late C-S-H forms as close as possible to its Ca/Si source, so
  densification starts next to unreacted clinker and moves outward. The
  "two types of C-S-H" work means inner versus outer product. B and that
  work should be one design. Inner product could be defined by site
  history (`initialMicroPhaseId_`).
- **Diffusion.** My "diffusion is fast at the voxel scale" held only for
  D ≈ 10⁻¹² m²/s. A 1 µm late-age rim limits the rate only if
  D ≲ 10⁻¹⁵–10⁻¹⁴ m²/s. At D = 10⁻¹³ (S55 value) it barely throttles, which
  is consistent with S55/S65. The shell throttle and proximity-graded
  densification hinge on the same unmeasured number: D through inner
  product. Jander fits are not diagnostic: the PSD, impingement and space
  filling give the same deceleration, and in-place inner product means
  less material must cross the shell than a shrinking-core model assumes.
- Jennings 2000/2008 (`~/Documents/Papers/Jennings/`) to be read when B is
  designed. No better data than Muller 2013 is known.

## Known Limitations published (alpha-3 and alpha-3.1)

Items 9–12 added with Jeff's approval:
- sealed runs create water (fixed in alpha-4);
- equilibrium is always computed at 25 °C (fixed in alpha-4);
- `_Enthalpy.csv` is not a heat of hydration (not yet fixed);
- low-w/c sealed runs stop early but show as Completed (fixed in alpha-4).

The alpha-3 body has CRLF line endings and was edited at the byte level;
alpha-3.1 replaces its "water fix held back" paragraph.

## Decisions for alpha-4

- The four remaining DEFERRED items (`checkICMoles`, `recordFailure`,
  fatal `calculateSI`, `_Enthalpy.csv` offset) wait until after alpha-4.
- Six steps agreed:
  1. Write `release-notes-alpha-4.md` (state plainly that results change).
  2. Bump the version (`app_info.py`, `.iss`, spec CFBundle strings).
  3. Build the macOS app and smoke-test the bundle, including a sealed run
     (check the sidecar git hash and DCH sha256).
  4. Create a draft GitHub release with the macOS zip.
  5. On Windows: sync, `build-windows.sh`, PyInstaller, Inno Setup, smoke
     test. This is the first Windows compile of everything since S66, so
     expect MinGW fixes.
  6. Attach the installer and publish.

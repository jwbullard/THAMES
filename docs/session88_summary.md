# Session 88 (Nov 17, 2026): alpha-4.3 fixes, log-normal PSD bug, VCCTL PSDs recovered

Started as a one-row sandbox cleanup for the Ep 8 (Mortar and Concrete) dry run
and became most of the alpha-4.3 patch. Jeff decided: fix every Elastic issue now
and ship 4.3 before Ep 8. All UI-side Python; backend unchanged (6.0.0).
Nothing pushed until the wrap-up commit.

## Grading editor (alpha-4.3 item 1)

- **Entry is cumulative % passing** (ASTM C136/C33 convention); storage stays
  individual % retained, so templates, `.gdg`, Elastic, Concelas and `elastic.c`
  are unchanged. Conversion in two module functions in `widgets/grading_curve.py`
  (`passing_to_retained`, `retained_to_passing`, `validate_passing`):
  excess above the top sieve counts as retained on it; material passing the
  finest sieve counts as retained on it (no pan row). Blank row = sieve not used.
- Plot is now the standard chart: % passing (linear) vs log sieve size, range
  from the sieve set. The old plot was cumulative % retained, transposed, and
  capped at 100 %, which hid the C-33 template's 262 % total.
- Removed: Preset, Type, Normalize, Smooth. Status line shows the first error or
  the no-pan note. OK and Save As Template refuse an invalid table. Editing a
  loaded template clears its name. Rows show sieve and opening ("No. 4 (4.75 mm)").
- Coarse table gained No. 8 and No. 16 (C 33 coarse sizes); checked that
  Concelas keeps fine and coarse classes separate, so the overlap is harmless.
- Fresh dialogs open on C-33 (fine) or #57 (coarse).
- Migration `20261117_01_grading_templates_percent_retained`: C-33 and #57 get
  C 33 mid-band values; `Manual Test Grading` and `standard_fine_grading` deleted.
- Also fixed: Manage Templates preview read a nonexistent `percent_passing` key;
  `.gdg` import/export used `percent_passing` keys (export KeyError, import stored
  zeros); file chooser left open behind its own message (hang); dead
  `create_standard_gradings` and empty-grading seeding deleted.
- Tests: `tests/test_grading_conversion.py` (16).

## Elastic Moduli (items 2-8)

- **2:** each mix stores its applied grading points
  (`mix_design.fine/coarse_aggregate_grading_data`, migration
  `20261117_02_mix_design_grading_data`). Save Mix now also saves template names.
  Load restores points (it used to fail on a nonexistent `template.grading_data`).
  Elastic writes the stored points; generic template fallbacks now warn. Jeff
  verified end to end. Hidden VCCTL row-grading button + dialog deleted.
- **3:** hydration copies `cement_psd.csv` from the mix folder; Elastic falls back
  to the mix folder for older runs. Jeff verified ("Copied cement PSD...").
- **4:** Elastic form all read-only (values from the mix), ITZ checkbox hidden
  (always on with aggregate), Generate Input File and override Browse removed.
  Jeff first proposed what-if overrides, then rejected them (provenance: many
  concretes under one hydration folder); issues filed in DEFERRED.
- **Unique operation names** (Jeff's request): `src/app/utils/operation_names.py`;
  Elastic (auto-fill + Start) and Hydration (Run + Load from previous) append
  `-01`, `-02`. A reused name used to overwrite files, delete the earlier Elastic
  record, and leave the new run without an Operations record.
  `create_operation_with_lineage` now refuses same-name Elastic/Operation records
  instead of deleting them. Mix Design already blocked duplicates.
- **5:** ITZ viewer detects the format past the `#` provenance line (48 layers
  read from a real run).
- **6:** Effective Moduli names via a word map (Young's, Poisson's, ITZ,
  volume fraction).
- **7:** Mix Design air spin max 0.15 (model limit).
- **8 a/b/d/e:** `Result/ConcelasStatus.txt` + red note in the viewer when concrete
  moduli are missing; `.gdg` written only into the run folder at launch (no
  strays in the Operations root; also fixed a same-day bug where selecting a
  microstructure created the run folder and Start renamed the run to `-01`);
  slab docstring (2 voxels, 3 if x is odd); `elastic_strain_viewer.py` deleted.
  **8c open:** Elastic VF uses fixed densities 2650/3150 vs Mix Design SGs.

## Log-normal PSD bug (every release since Session 7)

- `micgen_input_service._discretize_log_normal` normalized the density per um at
  log-spaced class centers (weights each class by 1/d). MyCement (median 10, sigma
  2) was generated with d50 0.74 um instead of ~9; cement_psd.csv gave ITZ width
  0.735 um (Jeff spotted it). Custom and Rosin-Rammler were fine.
- Fixed with CDF differences across geometric-midpoint edges;
  `tests/test_lognormal_psd.py` (4). "Std Dev" relabeled "sigma of ln(d)" with
  tooltip (portland cements ~1-1.5).
- micgen and `cement_psd.csv` now use the **stored table for every mode**; model
  parameters only when no table exists (Jeff: measured PSDs never carry a model).
  Parser accepts the older `{"diameter", "mass_fraction"}` form.

## VCCTL measured PSDs recovered

- ustype1, dh, cementhoc, cementrci reached THAMES as Log-Normal with no data;
  cement116 (Rosin-Rammler), cement168 (sigma 3) and sacci-425 also not measured.
- Source: VCCTL 9 Derby DB in `~/Code/VCCTL/data/database/vcctl_cement`, readable
  only at `f2eb05a0^` (that commit removed `seg0/cd1.dat`; the repo DB is
  unbootable since). Read on copies with the repo's `derby.jar`.
  The rescued Flyway SQL scripts in `~/Archive/OneDriveRescue-2026-09-19` are
  zero-filled.
- 31 files + mapping + README in `docs/reference_data/vcctl_psd/`. 28 THAMES
  tables match exactly. Migration `20261117_04_vcctl_measured_psd` (data in
  `src/app/database/vcctl_psd_data.py`) gives ustype1 (= cement151 psd),
  cement116, cement168, sacci-425 their measured tables. dh, cementhoc,
  cementotc, cementrci have no PSD file in VCCTL either: Jeff will search archives.
- **Duplicate shared the original's PSD record** (cement133 and
  "cement133 (Copy 1)" in Jeff's real DB, so editing the copy would change
  protected cement133). Duplicate now copies the record; migration
  `20261117_03_split_shared_psd` splits existing shares (runs before 04).

## Data changes outside the repo

- **Incident:** two import checks ran without a scratch HOME and applied
  migrations 01/02 to Jeff's real DB, including interim #57 values; #57 was then
  set to final values (backup `thames.db.pre-57-final-20261117`). Rule saved:
  memory `feedback_scratch_home_for_imports.md`.
- Sandbox: deleted the mistaken grading template; deleted two stray `.gdg`;
  MyCement's PSD record set to cement151's measured table (backup
  `thames.db.bak-20261117-before-mycement-psd`). Jeff will regenerate MyPaste and
  its hydrations off-camera and re-record Ep 7 (Eps 4-6 stand).
- Real DB Operations root has 3 old stray `.gdg` files (left alone).
- One Create Mix showed a 13 s UI stall between two trivial log lines; judged a
  one-off (add a watchdog if it recurs).

## Next

1. Jeff tests in the sandbox: relaunch (migrations 03/04 apply), grading editor,
   Elastic twice on the same microstructure (`-01`), ITZ viewer, Effective Moduli
   names, MyPaste regeneration.
2. Item 8c (size the density mismatch first).
3. Release steps: `release-notes-alpha-4.3.md` (log-normal and measured-PSD
   entries change results), Known Limitations on published alpha-3..4.2 (ask
   before `gh release edit`), version bump, macOS + Windows builds.

---

## Continued, Nov 18: alpha-4.3 release work

Commits `e7cec4aa`, `c932ffe3`, `563d949a`, `ed6e2bef` (pushed).

- **Grading import** no longer rescales totals below 100 (remainder passes the
  finest sieve; Jeff's `FineAdjust.gdg`); the table and storage now agree.
- **Item 8c:** Elastic volume fractions use the Mix Design formula with the
  materials' SGs.
- **One Operations record per Elastic run:** the Operations panel reuses the
  QUEUED record that Elastic already created. Since S3, every Elastic launch
  logged `UNIQUE constraint failed: operations.name`.
- **Release notes** `release-notes-alpha-4.3.md` (Jeff-edited; KL 17 ships).
  Version `1.0.0-alpha.4.3` in `app_info.py`, `.iss`, spec.
- **Ship-blocker found in the bundle:** `MigrationManager.__init__` created an
  unused `migration_scripts` folder; inside PyInstaller that fails, so **no
  migration has run in any packaged release since alpha-3**. mkdir removed
  (`563d949a`); an upgrade test on 4.2's shipped DB applied all six 2026
  migrations. Notes item 16 added.
- **macOS:** zip 673,832,469 bytes, SHA-256 `2d218c10…`, backend 6.0.0
  `6e49f9a7` (bundled `thames` identical to `bin/thames` apart from rpath;
  smoke fixture matches 4.2). Draft prerelease created, no tag.
- **Known Limitations for published pages:** untracked draft
  `release-notes-KL-amendments-alpha-4.3.md`, entries A-G; apply after
  publishing, one page at a time with Jeff's OK.
- **Windows handoff:** `docs/alpha-4.3-windows-build.md`.

### Next

1. Windows installer per the handoff doc; then on the Mac upload, fill in the
   size, publish, apply KL A-G.
2. Not yet filed: the ServiceContainer's migration error is printed before
   logging is configured, so it never reaches `thames.log` (that is why the
   bundle bug went unseen for three releases).
3. Videos: install the 4.3 build as the recording app, re-make MyPaste and
   Ep 7 off-camera, then Ep 8.

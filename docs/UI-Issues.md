# THAMES UI issues found while scripting Episode 3 (2026-10-22)

From a read of `~/Code/THAMES/src/app` at alpha.4.1. For a THAMES session; none block recording if kept off camera.

## Bugs

- **≡ Tools / View items open the wrong tab.** `switch_to_tab` (windows/main_window.py:1229-1244) still uses the old 8-tab numbering from before Microstructure and Files were removed.
  - Microstructure Parameters → Hydration · Hydration Simulation → Elastic Moduli · File Manager → Operations · Operation Manager → Results · View → Results does nothing
  - `get_current_tab_name` (:1254) has the same stale list, so **F1** context help is wrong from Hydration onward
- **Main window can't be resized by dragging** on macOS (seen in the Ep 2 dry run). `set_resizable(True)` is set; probably the GTK header bar (client-side decorations) on Quartz.
- **THAMES goes unresponsive to clicks after a display-scaling change** while running; needs a relaunch.
- **`thames.log` grows every second** with `STEP_DEBUG: … 'Process completed'` for finished operations (18 MB in one day).
- **View → Fullscreen** toggles on `is_maximized`, so it probably can't leave fullscreen (:713-720).

## Stubs visible in the UI

- ≡ File → New Project / Open Project (:500, :527)
- Materials → Import (materials_panel.py:511); cement details image "temporarily disabled" (:1699)
- Mix Design → Export (mix_design_panel.py:1080)
- Operations → Export Logs (:3680); Start opens a generic dialog that bypasses the panels (:3724)
- Keyboard shortcuts: nearly all registered shortcuts only log (ui/keyboard_manager.py:554-708); dialog not in any menu

## Stale text

- Home: "Key Features" and "Getting Started" are VCCTL-era wording (main_window.py:979-1033). Getting Started skips Hydration and Elastic Moduli; mentions "Project Management".
- Operations → Results Analysis sub-tab: "genmic", "VCCTL Operations Results Analysis Report" (:5169, :5346)
- Hydration and Operations panels lack the (i) help button the other panels have

## Seen in the Ep 3 take (2026-10-22)

- Results list shows a row **microstructure_metadata · Unknown Analysis** alongside the real runs
- Results Summary: "3D Microstructures: 1 files available" (plural)
- Results tab has only **View Results**; the Ep 3 sheet's **Plot Data** button doesn't exist

## Materials tab (found while scripting Ep 4, 2026-10-22)

- **Columns** button has no menu attached — does nothing (widgets/material_table.py:170-175)
- **Type** column and details pane say "thames" for every material (material_table.py:457; materials_panel.py:722, :1232)
- Header subtitle says it manages aggregates; aggregates are only on Mix Design (materials_panel.py:127; `AggregatePanel` never added)
- Search placeholder says "name, type, or properties"; it matches name and tags only (material_table.py:516-521)
- Built-in cements: `has_clinker=1`, `is_clinker=0` → dialog shows Material Type **Simple Material** and hides their stored surface fractions / correlation files
- **Specific Surface Area** has no unit label (m²/kg)
- "Particle Size Distribution" label appears twice (expander + inner frame)
- **Clear Filters** resets SG range to 1.0–5.0, but the initial range is 2.0–4.0
- Built-in cements have no tags, so the tag filter can't find any cement
- Read-only banner: "migrated from VCCTL"
- Material Details pane is sparse (name, "Thames", type, SG only)

## Mix Design tab (found while scripting Ep 5, 2026-10-23)

- (Not a bug — corrected 2026-10-23: aggregate mass > 0 makes micgen add a 2-voxel aggregate slab at X/2 for the ITZ, by design; aggregate masses, grading and air feed the Elastic Moduli calculation. Air is excluded from the paste microstructure on purpose.) Possible UI improvement: say so near the aggregate controls, since nothing on screen explains what aggregate mass does to the microstructure.
- **Total Volume Fraction** uses hard-coded SG 3.15/2.65, normalized → always ~1.000
- **Normalize** button is a stub ("not applicable for absolute masses") (mix_design_panel.py:811)
- **Export** stub confirmed (:1078-1081)
- W/B tooltip "Water mass / Powder mass" vs Water Mass tooltip "Binder = Paste = Powder + Water" — contradictory
- Voxel budget "Exceeds limit (27,000,000 max)" is advisory only; blank until a size changes
- Empty Mix Name passes the name check, then fails at auto-save with "❌ Auto-save failed!"
- Validation errors don't disable Create Mix; they only stop it at click time
- Metadata written for `<name>.pimg` instead of `<name>.thames.pimg` (:3649)
- Aggregate mass limit 10 kg vs powder 10000 kg
- Subtitle "Design concrete mixes…"; VCCTL names in progress map
- PSD classes under 0.5 voxel are silently dropped (micgen_input_service.py:883-914) — worth a UI warning
- Phases missing from the phase mapping are silently skipped (:1133-1135)

## Composite materials via "Add from Material" (raised 2026-10-28, code reading only — not tried in the app)

Decision for the THAMES session: **fix it or remove the button** from the Materials page. Jeff's question: can a viewer make a blended powder (e.g. 0.9 MyCement + 0.1 MyLimestone) as one material in the Materials tab, then use it alone in Mix Design, and get the same result as adding the two components in Mix Design?

- **What it does:** Add Material → Phase Composition → **Add from Material** copies the chosen material's *phases*, scaled by the mass fraction, into the new material (`phase_composition_editor.py:237`). The source materials are not kept as separate components (the `material_component` table exists, but nothing in the UI or micgen uses it).
- **Probably fails at Create Mix:** the clinker link (`clinker_source_id`, hence `has_clinker`) is set only when the source material is of type **Clinker** (`phase_composition_editor.py:286`; `thames_material_dialog.py:735`). Built-in cements and duplicates like MyCement are `is_clinker=0, has_clinker=1`, and the sandbox has **no** Clinker-type materials. So a composite made from a cement gets `has_clinker=0`, and micgen input generation should raise "No clinker material found in mix, but clinker volume fraction > 0" (`micgen_input_service.py:1721`). Confirm in the app first.
- **Not equivalent even if fixed:** micgen places particles phase by phase, and every phase of a composite gets the composite's single PSD and particle shape. The calcite still forms separate particles, but loses MyLimestone's own PSD (log-normal, 5 µm) and real shapes. That is an **interground** powder, not a **blended** one. Could be a legitimate feature if labeled as such.
- **If fixed:** carry the clinker link and correlation data over when the source is a cement with `has_clinker=1`, and say on screen that the composite uses one PSD and one shape. Possible use: Ep 10 (SCM case study), interground vs blended.
- **If removed:** drop the button and the unused `material_component` model, or hide it until it works.

## To-dos raised by Jeff (2026-10-28) — fix in the THAMES session

- [ ] **Random Seed tooltip is wrong.** It says "Seed for random number generation (0 = random)" (`mix_design_panel.py:4476`), but the seed must be a **negative integer** (spin range −2147483647 to −1). Fix the text, e.g. "Seed for the random number generator: a negative integer. Same seed + same inputs = same microstructure. Use Generate for a new one." Also check the Generate button tooltip (:4486) matches.
- [ ] **Tooltips pop up wherever the mouse rests on the Mix Design page**, even over empty areas with nothing to enter. Distracting (also on camera). Wanted: a tooltip only when hovering a data-entry label/control, or better a dedicated **"?" icon** beside each field that carries the help text. Cause not found by reading the code: the panel's 50 `set_tooltip_text` calls are all on labels, buttons and inputs, none on containers, so first reproduce and note **which tooltip text** appears over the empty area (that names the widget). Suspects: a widget whose allocation stretches across the row (hexpand/fill in a grid or box), or a GTK3-on-macOS tooltip quirk. Check the other tabs for the same behavior. If going the "?" route, do it app-wide with one helper, and rewrite the stale tooltips (W/B vs Water Mass conflict above) at the same time.
- [ ] **Kinetic-model hint text is too narrow** (Hydration → Phases → pencil / Edit Kinetics… → model dropdown). The gray line under the dropdown comes from `KINETIC_MODELS` in `phase_config_dialog.py:46-48`:
  - **Standard:** now "Sulfate phases (Gypsum, Bassanite, Anhydrite)" — reads as if Standard applies only to sulfates. Change to **"Typical for non-silicates"**.
  - **Pozzolanic:** now "Pozzolanic phases (Quartz, Fly ash, Silica fume)". Change to **"Pozzolanic phases (Aluminosilicate glasses, silica fume)"**.
  - ParrotKilloh ("Clinker phases (Alite, Belite, Aluminate, Ferrite)") unchanged unless Jeff says otherwise.
- [ ] **Kinetics column reverts to the default after the list is rebuilt** (Hydration → Phases). Seen by Jeff: calcite set to **Standard** in Configure Phase; on returning to the Hydration page the column shows **Thermodynamic**, but the pencil dialog still says Standard. Cause (code reading): `_populate_product_tree()` fills the Kinetics column from `kinetic_defaults.get_kinetic_type()` (`hydration_product_selector.py:274, 345, 705`) and ignores the user's choice in `self.kinetic_configurations`, which the dialog reads. Any rebuild resets the display: microstructure phases set (:944), cement type change (:643), search filter (:654), selection reset (:831, :962). The run itself uses `get_all_kinetic_configurations()` (`thames_hydration_panel.py:1498`), so it should get Standard — **confirm in the run's simparams.json**. Fix: when populating, use `self.kinetic_configurations[gems_name]['type']` if present, else the default.
- [ ] **Cement Type dropdown only ever adds phases (raised 2026-10-30).** Hydration → Cement Type. Jeff saw Portland and Limestone give the same checked list, with hemi- and monocarboaluminate checked under Portland. The per-type lists do differ (`SUGGESTED_PRODUCTS`, `hydration_products_service.py`): Portland has no carboaluminates and Limestone has them. But `_select_suggested_products` (`hydration_product_selector.py:735`) only adds to `selected_products` and never removes, and `_on_cement_type_changed` (:637) calls it on every change. So each type chosen piles onto the last, and going back to Portland keeps Limestone's phases. The Select Suggested button has the same behavior. From a code reading; not yet tried in the app.
  - **Fixing this alone is not enough: the lists themselves need work.** They read as add-ons to Portland, not complete sets, and only look sensible because they accumulate on top of the default Portland list. If a change replaced the selection, Limestone would have no `ettr`, no `ettr-AlFe` and no monosulfate phases; Slag no `ettr` or monosulfate; Pozzolanic neither, and it would also check all the glass phases and `Sfume` as products. Blended has `ettr` and `monosulf-AlFe` only.
  - **Decide:** (a) make each type a complete list and have a change replace the selection (keeping any phases in the microstructure); or (b) keep them as add-ons, relabel the control to say so, and uncheck the previous type's additions on a change. (a) is clearer for a user. Either way, warn before overwriting phases the user checked by hand.
  - **Pozzolanic must not check glass phases or `Sfume` (Jeff, 2026-10-30).** None of them can be a hydration product: `C2AS(am)`, `CA2S(am)`, `CAS(am)`, `CAS2(am)`, `K6A2S(am)`, `Sfume` and `Mullite` (which never forms spontaneously as a hydration product) are either in the original microstructure or absent, so remove them from the Pozzolanic list. If they are in the microstructure they are already included through `set_microstructure_phases`. `C2ASH55`, `C3(AF)S0.84H` and `straetlingite` are real products and stay.
  - **Limestone includes `SO4_CO3_AFt`,** the phase behind the 5 h GEMS failure of `HydrationOf-MyPaste-Thermo` (2026-10-30; see `docs/DEFERRED.md` in THAMES). Settle whether it stays in that list when that entry is resolved.
- [ ] **"Load from previous hydration operation": choose which microstructure to start from (raised 2026-11-02).** Hydration → radio button, `thames_hydration_panel.py:238-243`. Wanted: pick any microstructure from the previous operation, initial or any output age; the phase list updates to match; all other settings carry over and stay editable.
  - **What it does now:** Jeff expected the final microstructure to be used, but the code uses the **original starting microstructure**. `_restore_microstructure_for_loaded_op` (:1870) restores the file named in the config, and the log says "will run against the same voxels as the previous run." So today it means "rerun with changes." Neither the label nor the tooltip (:243) says so, and the microstructure combo is disabled in this mode (:1243). Whatever else happens, state this on screen.
  - **Bug: products can appear as locked microstructure phases (checked 2026-11-02; found by Jeff).** The voxels are the starting image: the copy in each hydration folder is byte-identical to the source in all seven pairs checked, across both operations trees. The phase list is what goes wrong. `thames_execution_service.py:231` copies the image into the hydration folder, and `_refresh_microstructure_list` (:1009) lists that copy too. The restore (:1919) takes the **first filename match** in a list sorted by folder name, so if `HydrationOf-…` sorts before the source folder, it picks the hydration copy. `_on_microstructure_changed` (:1279) then reads that folder's mapping, which also lists every product allowed in that run, and `set_microstructure_phases` (:924) locks them all. Sandbox: `MyPaste` shows 21 phases instead of 9, with `CSHQ`, `Portlandite`, `ettr` and others locked. It depends on the name: `FirstPaste` sorts before `HydrationOf-`, so it picks the source and is unaffected. `HydrationOf-MyPaste-Thermo` picks `HydrationOf-MyPaste`, which is a **different run's** mapping (same phases in this case, but not in general). Restore fallback (B) (:1927) hits the same problem, and choosing a `HydrationOf-…` copy by hand in New Simulation should too. **Effect on a run:** those products can't be unchecked, so a change to the product list in a reloaded run can't remove them; the voxels are still correct. **Required behavior (Jeff, 2026-11-02):** after Load, the locked top list must contain only the phases really in the initial microstructure, and must look exactly as it does for a new hydration operation from that same microstructure. `CSHQ`, `Portlandite` and other products must not appear there or be locked. Products checked in the previous run stay checked in the normal product list, where they can be unchecked. **Fix:** leave hydration-folder copies out of the list and resolve the source operation, or take the phases from the ids in the image, which also serves the age chooser below. Traced from the code and the real folders; the list-matching logic was reproduced in a script, not run in the app.
  - **Images available:** each output age is `Result/<op>.000y007d00h00m.298K.img`, and the starting image is in the operation folder and in `Result/`. The microstructure list skips the `Result/` folder, so a new per-operation chooser is needed. It should list ages in time order.
  - **Phase list:** a hydrated image holds phase ids in that operation's numbering, and `<op>_phase_mapping.json` covers them (checked on `HydrationOf-FirstPaste-done`: 20 ids in the mapping, 12 in the 7 d image). But `_on_microstructure_changed` (:1279) looks for the mapping as `<parent folder>_phase_mapping.json`, which for a `Result/` image is `Result/Result_phase_mapping.json`, so it would find nothing. The mapping also lists every phase allowed in the run, including products with no voxels, so counting the ids in the chosen image is what shows which phases are present. Solids that are products in the old run become starting phases in the new one, so the kinetics they carry over need a check. Phase ids must stay contiguous.
  - **Restarting from a hydrated image is not a supported path yet; this is more than a UI change.** The image holds phase ids only. It has no pore-solution composition and no kinetic or sub-voxel state (degree of reaction, gel densification). In Session 77 GEMS re-equilibrated a 28 d image on restart (portlandite 0.117 → 0.223; `docs/session77_summary.md:71`). Hydrated images also have no `.pimg`, so `InitialSet`/`FinalSet` would stay empty, and the run's clock starts again at 0. Age and maturity outputs would then read from the restart, not from mixing.
  - **Decide:** (a) UI only: offer the initial microstructure and label output ages as an experimental restart with these limits; or (b) add real restart support, which means the backend saves and reloads state at each output age, then the UI offers every age. Going with (b) makes this a backend job (`docs/DEFERRED.md`), not a UI-session item.

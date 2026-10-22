# Session 86 (Oct 22, 2026): alpha-4.1 prepared as a public prerelease

Short Mac session. Jeff decided to publish 1.0.0-alpha.4.1 (until now an
internal build for the tutorial videos) as a separate GitHub prerelease on the
alpha-3.1 pattern, because the Ep 2 end card points viewers to `/releases`.
Commits `78767261`, `effc5e56` + this wrap-up (pushed).

## Checks before releasing

- **`config/preferences.yml`**: only the dev UI's saved window position.
  Not part of the release.
- **`docs/figures/`**: the three PDFs for Jeff's untracked
  `gel_densification.tex`. Not part of the release.
- **Results unchanged vs alpha-4.** Ran the alpha-4 backend (`243c6165`,
  5.2.0, extracted from the published zip; needs `libpng16.16.dylib` one level
  up) and the alpha-4.1 backend (`6e49f9a7`, 6.0.0) on the Ca11mM smoke
  fixture: all 33 output files byte-identical apart from `#` headers, except
  `_CSH.csv`, which gains the last column `GelPorosityAllen` with every
  existing column identical.

## Release preparation

- **Release notes** `release-notes-alpha-4.1.md` (`78767261`, Jeff-edited):
  covers everything since alpha-4, not only banner/icon/version: Stop writes
  "Stopped by user" (alpha-4 KL 13), Resolution field removed (KL 14), final
  time in hours, Windows-authored operation folders on macOS/Linux,
  `GelPorosityAllen`. States that results do not change.
- **macOS asset** `dist/THAMES-1.0.0-alpha.4.1-macOS.zip` from the Oct 20
  `dist/THAMES.app`: 675,250,874 bytes, SHA-256 `04707cf6…7d4c1`.
- **Draft prerelease** "THAMES 1.0.0-alpha.4.1" created with
  `gh release create --draft --prerelease --target main`, macOS zip and notes
  attached. No tag until publish; the draft's URL is a temporary `untagged-…`.
- **Windows handoff** `docs/alpha-4.1-windows-build.md` (`effc5e56`). Unlike
  alpha-3.1, the backend must be rebuilt (`build-windows.sh clean`) so the
  installer ships 6.0.0; the handoff gates Inno Setup on a run reporting
  6.0.0 / `6e49f9a7`. Also: first real `pre-session-sync.sh` run under MSYS2
  since the LF conversion, and a check that the HiDPI banner looks right on
  Windows.

## Next

1. **Windows session:** follow `docs/alpha-4.1-windows-build.md` (build,
   six-point smoke test, copy the installer to the Mac).
2. **Mac:** `gh release upload` the installer to the draft, add sizes to the
   Downloads lines, publish (creates tag `v1.0.0-alpha.4.1`), tag the backend
   `v6.0.0` at `6e49f9a`.
3. Science thread unchanged: memory `project_late_age_csh_pore_physics.md`.

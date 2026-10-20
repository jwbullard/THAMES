# Session 85 (Oct 20, 2026): new banner, version label, tagline, app icons

Short UI-branding session; no backend or science work. Commits `ce553bbc`,
`beb3d83e` (pushed) and this wrap-up.

## Home page (`ce553bbc`)

- **Banner.** The icon + "THAMES" + subtitle header in
  `main_window.py::_create_home_tab` is replaced by one image,
  `icons/thames-banner-light.png`, centered at 700 px and loaded at the
  monitor's scale factor (cairo surface) so it is sharp on Retina.
- The banner comes from the tutorial project's
  `~/Teaching/Tutorials/THAMES-Videos/Graphics/Tools/banner.py`, run with
  `PAPER` overridden to pure white (the script's default is #FAFAF7, a faint
  beige that showed against the page). Built from `Icon-Teal-1024.png`.
  `Banner-Light.png` in the tutorial folder still has the beige paper.
- **Version label.** The bottom-right `v10.0.0` was VCCTL's hard-coded
  `app_version` in `application.py`; it now comes from
  `app_info.APP_VERSION` (shows `v1.0.0-alpha.4`; full prerelease tag kept on
  purpose). Same stale value in exported project metadata
  (`main_window.py`, `_gather_project_data`) fixed.
- **Tagline.** "Developed by Texas A&M University" removed (credited in the
  corner); description now "An integrated cement hydration simulation package
  using the GEMS3K library".

## App icons (`beb3d83e`)

Teal tower tile replaces `icons/thames-icon.png` (window icon, About logo),
`src/app/resources/icon.ico` (Windows app + installer, 16-256 px) and
`icon.icns` (macOS). Same file names, so no code, spec or `.iss` change.
macOS icon follows Apple's grid (824 px tile on a 1024 canvas); the others are
full-bleed. `.icns`/`.ico` are only visible in a packaged build.

## Left as is

VCCTL leftovers in `application.py`: internal `app_name = "VCCTL"`, CLI epilog
naming NIST, and application ID `edu.tamu.vcctl.gtk` (changing the ID may
affect how macOS tracks the app; needs its own decision).

## Next

Science thread unchanged: start from memory
`project_late_age_csh_pore_physics.md` (S84 design: Muller-scale gel curve,
fine capillary class carried by hydrate voxels, digitize Muller Fig. 2).

## Continued: 1.0.0-alpha.4.1 internal build (`c2305717`)

- **Version bumped to `1.0.0-alpha.4.1`** in `app_info.py`, the spec's macOS
  CFBundle strings and the `.iss` (`MyAppVersionDisplay` "1.0.0 (alpha 4.1)").
  Internal only, for the tutorial videos: **no tag, no GitHub release.** Both
  the home-page corner label and Help -> About read `APP_VERSION`.
- **macOS build** with PyInstaller (S67 GTK exports), `--clean`. Verified:
  Info.plist 1.0.0-alpha.4.1; `APP_VERSION` constant in the compiled PYZ;
  new banner, `thames-icon.png` and `icon.icns` in the bundle; `codesign
  --verify --deep --strict` passes. Bundled backend differs from `bin/thames`
  only in its rpath (`@loader_path/..`); smoke run with it reports 6.0.0
  `6e49f9a7`, exit 0.
- **Installed at `~/Applications/THAMES.app`** (1.3 GB). `dist/THAMES.app` is
  now this build (the published alpha-4 zips are untouched). Its backend
  differs from both published releases, so video results won't match an
  alpha-4 install exactly.

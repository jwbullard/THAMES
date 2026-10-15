# Session 82 (Oct 15, 2026): backend 6.0.0, Resolution field removed, tutorial project started

Short Mac session after alpha-4 was published. It closed two DEFERRED items and
started a separate video-tutorial project. Submodule `c380cb6` (pushed);
super-repo `d2a9c036` (pushed), `15aee172` and this wrap-up (local, not pushed
at Jeff's request).

## Backend version 6.0.0 (submodule `c380cb6`, super-repo `d2a9c036`)

CMake had reported 5.2.0 since Nov 2025, so the alpha-3 and alpha-4 backends
both said 5.2.0. Jeff chose 6.0.0 over 5.3.0 and approved folding in the
`VERSIONBUGFIX` cleanup.

- `CMakeLists.txt`: MAJOR 6, MINOR 0, PATCH 0; unused
  `THAMES_HYDRATION_VERSION` deleted.
- `src/version.h.in`: back-compat `VERSION` / `VERSION_MAJOR` /
  `VERSION_MINOR` macros deleted.
- `global.h`: `VERSIONBUGFIX` deleted.
- `Lattice.cc` (~line 193): `thamesVersion_ = THAMES_VERSION_STRING;`
- `AppliedStrain.cc` (~line 1256): writes `THAMES_VERSION_STRING` directly.

Rebuilt `bin/thames` reports 6.0.0, hash `c380cb62`. Smoke test in
`~/tmp/thames-alpha4-smoke` exits 0; the sidecar carries both values and image
headers read `#THAMES:Version: 6.0.0`. The input image still says 5.2 because
micgen wrote it. 93 build warnings, none in changed lines. The submodule is now
on branch `main`, not detached. DEFERRED entry marked LANDED.

## Resolution field removed (`15aee172`)

The Hydration page's Resolution field was never used: the backend reads
resolution from the image header (alpha-4 Known Limitation 14).

- `thames_hydration_panel.py`: widget, the `resolution=` argument to
  `HydrationInputConfig`, the log line, and the Load Operation restore.
- `hydration_input_service.py`: the field, its `to_dict` and `from_dict`
  entries.
- Both files are CRLF and stayed CRLF.
- An old `_hydration_config.json` containing `"resolution"` still loads.
- Jeff verified in the dev UI. DEFERRED entry marked LANDED.

## Clarifications

- "Dev app" = UI from source: `source thames-env/bin/activate; python src/main.py`.
- `bin/thames` is the backend only. `dist/THAMES.app` is the frozen alpha-4
  package (backend `243c6165`, reports 5.2.0).

## Tutorial videos (separate project)

Project folder `~/Teaching/Tutorials/THAMES-Videos/` (`Scripts/`, `Sandbox/`)
with its own memory directory; future tutorial sessions launch from there. Toolchain
(OBS + Source Record, Razer Kiyo Pro locked via CameraController, Mouseposé,
KeyCastr, DaVinci Resolve, whisper.cpp), sandbox via `HOME` override (GUI launch
not yet tested), the 12-episode series order, and the Episode 2 bullet sheet are
recorded there. UI fixes found while recording stay in this repo.

## Open

- Push `15aee172` and this wrap-up when Jeff says.
- Whether the alpha-3 / alpha-3.1 release pages should point to alpha-4.
- DEFERRED: CRLF sync scripts (convert to LF, `.gitattributes`
  `*.sh text eol=lf`); stopped-run sidecar fix in the UI; CRLF stripping on
  stdin paths in the backend.
- Science after alpha-4: option B (tracked sub-voxel pore population with
  inner/outer-product C-S-H), gel-water drawdown test, restoring
  `nucleatePhaseAff`.

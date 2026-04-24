# THAMES

**Thermodynamic Hydration And Microstructure Evolution Simulator**

[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](https://github.com/jwbullard/THAMES/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE.md)
[![Latest release](https://img.shields.io/github/v/release/jwbullard/THAMES?include_prereleases&label=latest)](https://github.com/jwbullard/THAMES/releases/latest)

THAMES is a desktop application for simulating cement hydration, microstructure
evolution, and the resulting elastic properties of hardened cement paste,
mortar, and concrete. It couples a C++ hydration engine
([THAMES-Hydration](backend/thames-hydration)) with the
[GEMS3K thermodynamic library](https://gems.web.psi.ch/GEMS3K/) and provides a
GTK-based interface for designing mix compositions, generating
3D microstructures, running adaptive-timestep hydration simulations, and
post-processing the results into multi-scale elastic moduli.

> **Status: alpha pre-release.**  
> File formats, simulation parameters, and the database schema may change in
> later releases. Save your work and do not rely on this build for results
> you cannot reproduce later.

![THAMES main window](docs/images/01-main-window.png)

---

## Download

Pre-built binaries are published as GitHub releases. Pick the latest pre-release
matching your platform:

- **Windows 10/11 (x64)**
  [Installer (.exe)](https://github.com/jwbullard/THAMES/releases/latest) —
  user-local install at `%LOCALAPPDATA%\Programs\THAMES\`, no admin required.
  Or [portable ZIP](https://github.com/jwbullard/THAMES/releases/latest) for
  managed environments where installers are blocked.
- **macOS** — DMG packaging is in progress; for now, build from source
  (see [docs/ALPHA_RELEASE_PREPARATION.md](docs/ALPHA_RELEASE_PREPARATION.md)).
- **Linux** — Build from source.

The installer and ZIP are not currently code-signed. Windows SmartScreen
will warn the first time you launch them: click **More info → Run anyway**.
Code-signing is planned for the beta release.

---

## Quick start

1. Install (or unzip and run `THAMES.exe`).
2. **Help → Getting Started** opens a pre-rendered section of the User Manual
   in your browser with figures and cross-references intact.
3. The typical flow:
   - **Materials** tab: review the bundled cement / fly ash / slag / filler
     database; add your own as needed.
   - **Mix Design** tab: pick a binder, set W/B ratio, optionally include
     fine and/or coarse aggregate and air content. Click *Generate
     Microstructure*.
   - **Hydration** tab: select hydration products to track, set the
     simulation duration and output cadence, click *Run*.
   - **Operations** tab: monitor the live simulation and access finished
     runs.
   - **Elastic Moduli** tab: pick a hydrated microstructure and run the
     elastic calculation. Aggregate-bearing microstructures additionally
     produce concrete-scale moduli via concelas.

Full documentation is in [docs/USER_MANUAL.md](docs/USER_MANUAL.md) (~1,200
lines, 32 figures) and is also available offline from the **Help → User
Guide** menu inside the application.

---

## Architecture

THAMES is built on the [VCCTL v10.0.0](https://www.nist.gov/services-resources/software/vcctl-software)
desktop architecture but with a different hydration engine and an
integrated thermodynamic solver:

| Layer | Component |
|---|---|
| Hydration solver | [THAMES-Hydration (C++)](backend/thames-hydration) |
| Thermodynamics | GEMS3K (100 phases, 198 dependent components, 277–353 K) |
| Microstructure generation | `micgen` (C, derived from VCCTL `genmic`) |
| Elastic moduli | Per-voxel finite-element solver + concelas concrete homogenization |
| User interface | Python 3.12 + PyGObject (GTK 3) |
| Build | PyInstaller + Inno Setup (Windows), PyInstaller + py2app (macOS) |

VCCTL uses per-material-type tables (`cement`, `fly_ash`, `slag`, …); THAMES
uses a unified `material` table with tag-based classification and per-material
GEMS phase composition. The hydration kinetics, GEMS coupling, and
multi-temperature support are all new.

---

## User data

THAMES keeps the installed program separate from your personal data:

- **Program** (created by installer): `%LOCALAPPDATA%\Programs\THAMES\`
- **User data** (created on first launch): `%LOCALAPPDATA%\THAMES\`
  - `operations\` — per-run working directories
  - `database\thames.db` — mix designs, materials, operation history
  - `aggregate\`, `particle_shape_set\` — extracted shape libraries
  - `materials\`, `usr\`, `logs\`

The uninstaller removes only the program tree; your operations and saved
mix designs survive uninstall + reinstall. To start fresh, delete
`%LOCALAPPDATA%\THAMES\` manually.

(macOS uses `~/Library/Application Support/THAMES/`; Linux uses
`~/.local/share/THAMES/`.)

---

## Reporting bugs and giving feedback

Please file issues at <https://github.com/jwbullard/THAMES/issues> with the
**`alpha-feedback`** label. Include:

- Version from **Help → About** (e.g. `1.0.0-alpha.2`)
- Operating system and version
- Steps to reproduce
- Any `*.log` or `exit_status.json` files from the affected operation
  directory under `%LOCALAPPDATA%\THAMES\operations\<name>\`
- Screenshots for UI issues

For sensitive or institutional questions: <jwbullard@tamu.edu>.

---

## Building from source

See [docs/ALPHA_RELEASE_PREPARATION.md](docs/ALPHA_RELEASE_PREPARATION.md)
for the full Windows packaging recipe. In brief:

```bash
# Windows (MSYS2 mingw64 + thames-env-windows venv with --system-site-packages)
./build-windows.sh                              # Builds C++ backend → bin/
pip install "markdown>=3.4.0"                   # Only pip-managed dep on Windows
pacman -S mingw-w64-x86_64-python-scipy         # MSYS2 supplies the rest
PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller thames-windows.spec --noconfirm
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\thames-windows.iss
```

Output: `dist\THAMES-1.0.0-alpha.2-setup.exe` (~105 MB) and
`dist\THAMES-1.0.0-alpha.2-win64.zip` (~760 MB).

---

## License

MIT License — see [LICENSE.md](LICENSE.md).

---

## Contributors

- **Jeffrey W. Bullard** (Texas A&M University) — Principal Investigator;
  overall project lead, application architecture, GTK interface, and
  release engineering.
- **Dr. Florin Nita** (Texas A&M University) — improvements to the
  performance and accuracy of the C++ hydration model.

---

## Acknowledgements

THAMES is developed at Texas A&M University. It builds on the original
VCCTL software developed at the National Institute of Standards and
Technology (NIST) and on the GEMS3K thermodynamic library developed at
the Paul Scherrer Institut.

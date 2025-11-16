# THAMES Project - Claude Context

## Project Overview

THAMES is a GTK-based application for advanced cement hydration simulation, using the THAMES-Hydration C++ simulator. This project is based on the VCCTL architecture but adapted for the upgraded hydration simulation engine.

**Based on:** VCCTL v10.0.0
**Hydration Engine:** THAMES-Hydration (C++)
**Started:** November 2025

## Key Differences from VCCTL

### Hydration Simulator
- **VCCTL:** Uses disrealnew.c (C implementation)
- **THAMES:** Uses THAMES-Hydration (C++ implementation)

### Input Generation
[To be documented during migration]

### Output Format
[To be documented during migration]

### Microstructure Generation
[To be documented during migration]

## Development Sessions

### Session 1: Repository Setup
November 15, 2025 (Morning)
- Created THAMES repository
- Copied VCCTL infrastructure
- Added THAMES-Hydration as git submodule
- Initial project documentation
- THAMES C++ code analysis

### Session 2: GEMS Integration & Materials Architecture
November 15, 2025 (Afternoon)

**Context**: THAMES requires GEMS3K thermodynamic database for phase definitions. Unlike VCCTL's fixed material categories (Cement, Fly Ash, etc.), GEMS has 92 phases that don't map to rigid types. Phases like "Aluminate" can appear in both cement AND fly ash.

**Key Accomplishments**:

1. **GEMS Database Integration** (`src/data/gems/`)
   - Added 4 GEMS3K database files: thames-dch.dat (32KB), thames-dbr.dat (15KB), thames-ipm.dat (20KB), thames-dat.lst
   - Database contains: 13 ICs, 180 DCs (chemical species), 92 GEM phases
   - Critical structure: `<nDCinPH>` array defines which DCs belong to which phase
     - Phase 1 (aq_gen): DCs 1-69 (aqueous ions)
     - Phase 2 (gas_gen): DCs 70-77 (gases)
     - Phase 3+: Solid phases (cement, pozzolans, etc.)

2. **GEMS Parser Service** (`src/app/services/gems_parser_service.py`)
   - 400-line service that parses thames-dch.dat key-value format
   - Auto-builds phase-to-DC mappings using nDCinPH ordering
   - API: `get_phase()`, `get_dcs_for_phase()`, `validate_phase_dc_configuration()`
   - Tested with `test_gems_parser.py` - all 92 phases verified

3. **Phase Mappings** (`src/app/config/phase_mappings.py`, `docs/vcctl_to_gems_phase_mapping.md`)
   - **Cement**: 9 phases (C3S→Alite, C2S→Belite, C3A→Aluminate, C4AF→Ferrite, GYPSUM→Gypsum, etc.)
   - **Limestone**: 4 phases (Calcite, Dolomite-dis, Dolomite-ord, lime)
   - **Fly Ash**: 8 typical phases (Quartz, Mullite, Aluminate, C2AS(am), CA2S(am), etc.)
   - **Key insight**: Phases are NOT exclusive - Aluminate in both cement & fly ash

4. **Materials Architecture Design** (tag-based system)
   - **Problem**: VCCTL has 5 rigid categories, but GEMS has 92 phases with overlaps
   - **Solution**: Materials = phase composition + flexible tags, NO kinetics
     ```python
     Material {
         name: "Portland Cement Type I"
         tags: ["cement", "type-i", "portland"]  # User-defined, searchable
         phases: [{gem_phase: "Alite", mass_fraction: 0.60}, ...]
         density: 3.15
         # NO kinetic parameters
     }
     ```
   - **Kinetics in Mix Design**: User defines model + parameters when adding material to mix
   - **Migration plan**: Cements & limestones from VCCTL → THAMES, fly ash/slag/fillers user-defined

5. **Virtual Environment** (`thames-env/`)
   - Python 3.11.13 with PyGObject 3.52.3 (pinned - 3.54.5 has brew issues)
   - All dependencies installed (GTK, SQLAlchemy, Pandas, PyVista, etc.)
   - Activate: `source thames-env/bin/activate`

**Files Created**:
- `src/data/gems/` - GEMS database (4 files)
- `src/app/services/gems_parser_service.py` - Parser (~400 lines)
- `src/app/config/phase_mappings.py` - VCCTL↔GEMS mappings
- `test_gems_parser.py` - Comprehensive tests
- `docs/gems_parser_summary.md` - API documentation
- `docs/vcctl_to_gems_phase_mapping.md` - Migration reference
- `requirements.txt` - Python dependencies
- `SESSION_SUMMARY_2025_11_15.md` - Complete session details

**Next Steps** (for next session):
1. Design tag-based Material database schema (flexible tags, phase composition)
2. Create migration script to read VCCTL cements/limestones and convert to THAMES format
3. Build Material creation service (CRUD, tag management, validation with GEMS parser)
4. Adapt Materials UI panel from VCCTL (tag-based search, phase editor)

**Critical Files for Next Session**:
- VCCTL database: `/Users/jwbullard/Software/vcctl-gtk/src/data/database/vcctl.db`
- Phase mappings: `src/app/config/phase_mappings.py`
- GEMS parser: `src/app/services/gems_parser_service.py`
- VCCTL cement service (reference): `vcctl-gtk/src/app/services/cement_service.py`

---

## MANDATORY: Cross-Platform Safety Protocol

**CRITICAL: Before making ANY change to these files, ALWAYS check both platforms:**
- `.spec` files (thames-macos.spec, thames-windows.spec)
- Path-related code (directories_service.py, config_manager.py, app_info.py)
- Build scripts (build_macos.sh, any Windows build scripts)
- Hooks directory

**Required checks for EVERY change:**

1. **Read BOTH platform spec files:**
   ```bash
   grep -n "relevant_pattern" thames-macos.spec
   grep -n "relevant_pattern" thames-windows.spec
   ```

2. **State explicitly BEFORE making the change:**
   - "This change affects: [macOS / Windows / both]"
   - "Windows currently does: [X]"
   - "macOS currently does: [Y]"
   - "After this change: [Z]"
   - "This will/won't break Windows because: [reason]"

3. **For path changes specifically:**
   - Check where files are bundled in BOTH specs
   - Check where code looks for them in the Python files
   - Verify the paths match on BOTH platforms after the change

**Failure to follow this protocol causes platform regressions and wastes user time.**

## Git commands
- Do not run a git command unless you are requested to do so
- Use "git add -A" to stage changes before committing to the git repository

## Responses
- Do not use the phrase "You're absolutely right!". Instead, use the phrase
"Good point.", or "I see what you are saying."

## OS Switching Procedures (CRITICAL - READ FIRST)

### **Cross-Platform Development Workflow**

When working on THAMES across multiple operating systems (Mac, Windows, Linux), use these scripts to keep git repositories synchronized:

#### **Starting Work on Different OS:**

```bash
./pre-session-sync.sh
```

**What it does:**
- Fetches latest changes from remote
- Shows what commits will be pulled
- Creates automatic backup branch
- Pulls changes with rebase strategy
- Verifies sync completed successfully

**When to use:**
- ALWAYS at start of session on different OS
- After long break between sessions
- When you suspect changes on remote

#### **Ending Work Session:**

```bash
./post-session-sync.sh
```

**What it does:**
- Shows all uncommitted changes
- Prompts for commit message (or auto-generates)
- Stages all changes with `git add -A`
- Creates commit with standard format
- Pushes to remote repository

**When to use:**
- ALWAYS at end of work session
- Before switching to different OS
- Before long breaks

---

## Key Technical Patterns

### PyInstaller Path Resolution:
```python
# WRONG - breaks in PyInstaller:
project_root = Path(__file__).parent.parent.parent

# RIGHT - use service abstraction:
operations_dir = self.service_container.directories_service.get_operations_path()
```

### Platform-Specific subprocess:
```python
popen_kwargs = {'stdout': ..., 'stderr': ...}
if sys.platform == 'win32':
    popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
process = subprocess.Popen(cmd, **popen_kwargs)
```

### Cross-Platform User Data Directories:
- **macOS:** `~/Library/Application Support/THAMES/`
- **Windows:** `%LOCALAPPDATA%\THAMES\`
- **Linux:** `~/.local/share/THAMES/`

---

# Important Instructions
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

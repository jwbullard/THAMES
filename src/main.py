#!/usr/bin/env python3
"""
VCCTL GTK3 Application Entry Point

Virtual Cement and Concrete Testing Laboratory
Desktop application using GTK3 and Python
"""

import sys
import os
import faulthandler
import traceback
from datetime import datetime
from pathlib import Path


def _user_data_dir() -> Path:
    """User-data dir matching app_info.py (avoids importing Gtk-dependent code)."""
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'THAMES'
    if os.name == 'posix' and os.uname().sysname == 'Darwin':
        return Path.home() / 'Library' / 'Application Support' / 'THAMES'
    return Path.home() / '.local' / 'share' / 'THAMES'


# Open a long-lived crash log BEFORE any heavyweight imports so we capture
# native crashes (segfaults in GTK/VTK/numpy DLLs) and otherwise-silent
# Python exceptions. Console=False in PyInstaller swallows stdout; without
# this, the process just disappears with no clue what happened.
_logs_dir = _user_data_dir() / 'logs'
_logs_dir.mkdir(parents=True, exist_ok=True)
_crash_log = open(_logs_dir / 'thames-crash.log', 'a', buffering=1, encoding='utf-8')
_crash_log.write(f"\n=== {datetime.now().isoformat()} startup pid={os.getpid()} ===\n")
faulthandler.enable(file=_crash_log, all_threads=True)


def _excepthook(exc_type, exc_value, exc_tb):
    _crash_log.write(f"\n=== {datetime.now().isoformat()} UNCAUGHT EXCEPTION ===\n")
    traceback.print_exception(exc_type, exc_value, exc_tb, file=_crash_log)
    _crash_log.flush()
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Dev-mode GSettings schema fix (macOS only, no effect when bundled).
#
# In a PyInstaller bundle the GI runtime hook points GSETTINGS_SCHEMA_DIR at
# Contents/Resources/share/glib-2.0/schemas, which carries the compiled
# gschemas.compiled cache. In dev mode (`python src/main.py`), GLib expects
# to find schemas via XDG_DATA_DIRS — which some terminals (Ghostty among
# them) override in a way that strips /opt/homebrew/share. `gsettings
# list-schemas` then returns nothing, and clicking GTK's ColorButton tries
# to open a color-chooser dialog that requires the
# `org.gtk.Settings.ColorChooser` schema and aborts the process via
# g_log_abort (SIGTRAP, no Python traceback). Point GSETTINGS_SCHEMA_DIR
# at Homebrew's compiled cache so dev launches work regardless of the
# terminal env.
if not getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    if 'GSETTINGS_SCHEMA_DIR' not in os.environ:
        _brew_schemas = Path('/opt/homebrew/share/glib-2.0/schemas')
        if (_brew_schemas / 'gschemas.compiled').exists():
            os.environ['GSETTINGS_SCHEMA_DIR'] = str(_brew_schemas)

try:
    from app.application import VCCTLApplication
except ImportError as e:
    _crash_log.write(f"Import error: {e}\n")
    print(f"Error importing application: {e}")
    print("Make sure GTK3 and PyGObject are properly installed.")
    print("Run: pip install PyGObject")
    sys.exit(1)


def main():
    """Main entry point for the VCCTL GTK application."""
    try:
        app = VCCTLApplication()
        return app.run(sys.argv)
    except Exception as e:
        _crash_log.write(f"Startup exception: {e}\n")
        traceback.print_exc(file=_crash_log)
        _crash_log.flush()
        print(f"Error starting application: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
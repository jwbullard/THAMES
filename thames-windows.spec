# -*- mode: python ; coding: utf-8 -*-
"""
THAMES PyInstaller Specification File
Cross-platform packaging for Windows, macOS, and Linux
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

# Platform-specific binary executables
if IS_WINDOWS:
    # THAMES ships only two compiled backends: the C++ hydration simulator
    # (thames.exe) and the C microstructure generator (micgen.exe). They live
    # in bin/ at the repo root — kept in sync by build-windows.sh — and are
    # bundled to bin/ inside the packaged app. Code paths that locate them go
    # through DirectoriesService.bin_path, which resolves both layouts.
    platform_binaries = [
        ('bin/thames.exe', 'bin/'),
        ('bin/micgen.exe', 'bin/'),
        ('bin/libpng16-16.dll', 'bin/'),
    ]
elif IS_MACOS:
    # THAMES on macOS ships the same two compiled backends as Windows: the C++
    # hydration simulator (thames) and the C microstructure generator (micgen).
    # Both live in bin/ at the repo root (produced by build-macos.sh) along with
    # the bundled Homebrew libpng16 dylib that build-macos.sh rewrites to
    # @rpath/libpng16.16.dylib so testers don't need Homebrew installed.
    platform_binaries = [
        ('bin/thames', 'bin/'),
        ('bin/micgen', 'bin/'),
        ('bin/libpng16.16.dylib', 'bin/'),
    ]
elif IS_LINUX:
    platform_binaries = [
        ('backend/bin-linux/genmic', 'backend/bin/'),
        ('backend/bin-linux/disrealnew', 'backend/bin/'),
        ('backend/bin-linux/elastic', 'backend/bin/'),
        ('backend/bin-linux/genaggpack', 'backend/bin/'),
        ('backend/bin-linux/perc3d', 'backend/bin/'),
        ('backend/bin-linux/stat3d', 'backend/bin/'),
        ('backend/bin-linux/oneimage', 'backend/bin/'),
    ]
else:
    platform_binaries = []

# Add GTK DLLs on Windows (MSYS2)
if IS_WINDOWS:
    import glob
    mingw_bin = r'C:\msys64\mingw64\bin'
    # Collect all GTK-related DLLs
    gtk_dlls = glob.glob(os.path.join(mingw_bin, 'lib*.dll'))
    for dll in gtk_dlls:
        platform_binaries.append((dll, '.'))

# Collect GTK/GI data files
gi_typelibs = collect_data_files('gi')

# Add Windows-specific GioWin32 typelib (not collected automatically)
if IS_WINDOWS:
    giowin32_typelib = r'C:\msys64\mingw64\lib\girepository-1.0\GioWin32-2.0.typelib'
    if os.path.exists(giowin32_typelib):
        gi_typelibs.append((giowin32_typelib, 'gi_typelibs'))

    # Add GLib typelib (may not be collected automatically on some systems)
    glib_typelib = r'C:\msys64\mingw64\lib\girepository-1.0\GLib-2.0.typelib'
    if os.path.exists(glib_typelib):
        gi_typelibs.append((glib_typelib, 'gi_typelibs'))

# Hidden imports for GTK and other dependencies
hiddenimports = [
    'gi',
    'gi.repository.Gtk',
    'gi.repository.Gdk',
    'gi.repository.GLib',
    'gi.repository.Gio',
    'gi.repository.GObject',
    'gi.repository.Pango',
    'gi.repository.GdkPixbuf',
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'pandas',
    'numpy',
    'matplotlib',
    'PIL',
    'yaml',
    'psutil',
    'markdown',
    'markdown.extensions',
    'markdown.extensions.toc',
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
    # Scientific computing - scipy used by micgen_input_service for log-normal PSD discretization
    'scipy',
    'scipy.stats',
    'scipy.ndimage',
    'scipy.sparse',
    'app',
    'app.application',
]

# Attempt to add pyvista if available (optional dependency)
try:
    import pyvista
    hiddenimports.extend([
        'pyvista',
        'vtk',
        'vtkmodules',
        'vtkmodules.all',
        'vtkmodules.util',
        'vtkmodules.util.numpy_support',
        'vtkmodules.vtkCommonCore',
        'vtkmodules.vtkCommonDataModel',
        'vtkmodules.vtkRenderingCore',
        'vtkmodules.vtkFiltersCore',
    ])
except ImportError:
    pass

# Attempt to add pydantic if available (optional dependency)
try:
    import pydantic
    hiddenimports.append('pydantic')
except ImportError:
    pass

# jaraco.text is needed on some systems
try:
    import jaraco.text
    hiddenimports.append('jaraco.text')
except ImportError:
    pass

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],  # Add src directory so app module can be found
    binaries=platform_binaries,
    datas=[
        # THAMES User Manual source + figures (in-app Help menu renders
        # USER_MANUAL.md to HTML on demand; figures resolve via <base href>)
        ('docs/USER_MANUAL.md', 'docs'),
        ('docs/images', 'docs/images'),
        ('src/app/resources', 'app/resources'),  # Include application resources
        ('icons', 'icons'),  # Include Carbon icons
        ('src/data', 'data'),  # Include database and data files
        ('particle_shape_set.tar.gz', 'data/'),  # Include compressed particle shape data (extracted on first launch)
        ('aggregate.tar.gz', 'data/'),  # Include compressed aggregate shape data (extracted on first launch)
    ] + gi_typelibs,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='THAMES',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/app/resources/icon.ico' if IS_WINDOWS and os.path.exists('src/app/resources/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='THAMES',
)

# macOS .app bundle (only on macOS)
if IS_MACOS:
    app = BUNDLE(
        coll,
        name='THAMES.app',
        icon='src/app/resources/icon.icns' if os.path.exists('src/app/resources/icon.icns') else None,
        bundle_identifier='edu.tamu.thames',
        info_plist={
            'CFBundleName': 'THAMES',
            'CFBundleDisplayName': 'Thermodynamic Hydration And Microstructure Evolution Simulator',
            'CFBundleVersion': '1.0.0-alpha.2',
            'CFBundleShortVersionString': '1.0.0-alpha.2',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.14',
            'LSApplicationCategoryType': 'public.app-category.education',
        },
    )

    # Post-bundle fix: replace PIL's bundled libharfbuzz with Homebrew's copy.
    #
    # PyInstaller's PIL hook bundles a minimal libharfbuzz built without
    # CoreText support, and on macOS PyInstaller resolves the canonical
    # Contents/Frameworks/libharfbuzz.0.dylib through PIL's copy (via a
    # symlink chain). But Homebrew's libpangocairo — which the GI hook
    # collects to run GTK — links against the Homebrew harfbuzz that DOES
    # have CoreText. Loading Gdk-3.0.typelib then fails with
    # "Symbol not found: _hb_coretext_font_create" and the app exits at
    # startup before any UI shows. Replacing the single physical PIL copy
    # (everything else points to it) with Homebrew's cures it.
    import shutil
    import subprocess
    bundle_root = os.path.join('dist', 'THAMES.app')
    target = os.path.join(bundle_root, 'Contents', 'Frameworks',
                          'PIL', '__dot__dylibs', 'libharfbuzz.0.dylib')
    homebrew_src = '/opt/homebrew/opt/harfbuzz/lib/libharfbuzz.0.dylib'
    if not os.path.exists(homebrew_src):
        raise RuntimeError(
            f"Homebrew libharfbuzz not found at {homebrew_src}. "
            "Install with: brew install harfbuzz"
        )
    if not os.path.exists(target):
        raise RuntimeError(
            f"Expected PyInstaller-bundled PIL harfbuzz at {target}, not found. "
            "PyInstaller bundle layout may have changed; re-investigate."
        )
    shutil.copy2(homebrew_src, target)
    os.chmod(target, 0o755)
    for cmd in [
        ['install_name_tool', '-id', '@rpath/libharfbuzz.0.dylib', target],
        ['install_name_tool', '-change',
         '/opt/homebrew/opt/freetype/lib/libfreetype.6.dylib',
         '@rpath/libfreetype.6.dylib', target],
        ['install_name_tool', '-change',
         '/opt/homebrew/opt/glib/lib/libglib-2.0.0.dylib',
         '@rpath/libglib-2.0.0.dylib', target],
        ['install_name_tool', '-change',
         '/opt/homebrew/opt/graphite2/lib/libgraphite2.3.dylib',
         '@rpath/libgraphite2.3.dylib', target],
        ['codesign', '--force', '--sign', '-', target],
        # Re-sign the parent bundle since the nested dylib changed.
        ['codesign', '--force', '--deep', '--sign', '-', bundle_root],
    ]:
        subprocess.run(cmd, check=True)
    print('[thames-spec] libharfbuzz: PIL copy replaced with Homebrew, '
          'install_names rewritten to @rpath/, bundle re-signed.')

# Building THAMES on Windows with MSYS2/MinGW

**Last Updated:** December 30, 2025

This guide explains how to build the complete THAMES system on Windows using MSYS2 and the MinGW-w64 toolchain.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Build Order](#build-order)
4. [Step 1: Build GEMS3K Library](#step-1-build-gems3k-library)
5. [Step 2: Build THAMES-Hydration](#step-2-build-thames-hydration)
6. [Step 3: Build Micgen](#step-3-build-micgen)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Quick Reference](#quick-reference)

---

## Overview

The THAMES build system consists of three components that must be built in order:

```
┌─────────────────────────────────────────────────────────────┐
│                     THAMES Application                       │
├─────────────────────────────────────────────────────────────┤
│  bin/thames.exe     │  bin/micgen.exe                       │
│  (Hydration engine) │  (Microstructure generator)           │
├─────────────────────┼───────────────────────────────────────┤
│  thameslib          │  thamesauxlib                         │
│  (C++ library)      │  (C library)                          │
├─────────────────────┼───────────────────────────────────────┤
│  GEMS3K-static      │  libpng, zlib                         │
│  (Thermodynamics)   │  (Image I/O)                          │
└─────────────────────┴───────────────────────────────────────┘
```

**Dependency Chain:**
1. **GEMS3K-standalone** -> produces `libGEMS3K-static.a`
2. **THAMES-Hydration** -> uses GEMS3K-static, produces `thames.exe`
3. **Backend (micgen)** -> uses libpng/zlib, produces `micgen.exe`

---

## Prerequisites

### Required Software

**MSYS2** must be installed. Download from: https://www.msys2.org/

### Required MSYS2 Packages

Open the **MSYS2 MinGW 64-bit** terminal and install:

```bash
# Update package database
pacman -Syu

# Install build tools
pacman -S mingw-w64-x86_64-gcc
pacman -S mingw-w64-x86_64-cmake
pacman -S mingw-w64-x86_64-make

# Install dependencies for micgen
pacman -S mingw-w64-x86_64-libpng
pacman -S mingw-w64-x86_64-zlib
```

### Verify Installation

```bash
# In MSYS2 MinGW 64-bit terminal
gcc --version      # Should show GCC 15.x or newer
cmake --version    # Should show CMake 3.26 or newer
mingw32-make --version  # Should show GNU Make 4.x
```

**Current versions on this system:**
- GCC 15.2.0
- CMake 4.1.2
- GNU Make 4.4.1
- libpng 1.6.50
- zlib 1.3.1

---

## Build Order

**IMPORTANT:** Components must be built in this exact order due to dependencies.

| Order | Component | Output | Location |
|-------|-----------|--------|----------|
| 1 | GEMS3K-standalone | `libGEMS3K-static.a` | `thames-hydration/Resources/lib/` |
| 2 | THAMES-Hydration | `thames.exe` | `thames-hydration/bin/` |
| 3 | Backend (micgen) | `micgen.exe` | `backend/build/` or `bin/` |

---

## Step 1: Build GEMS3K Library

The GEMS3K library provides thermodynamic calculations for THAMES-Hydration.

### 1.1 Open MSYS2 MinGW 64-bit Terminal

**IMPORTANT:** Use "MSYS2 MinGW 64-bit" from the Start Menu, NOT regular MSYS2 or Git Bash.

### 1.2 Navigate to GEMS3K Directory

```bash
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend/thames-hydration/src/GEMS3K-standalone
```

### 1.3 Build GEMS3K

The `install.sh` script is pre-configured for MinGW CMake, but the `make` command may not work. Build manually instead:

```bash
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend/thames-hydration/src/GEMS3K-standalone
rm -rf build
mkdir build
cd build

# Configure
cmake -G "MinGW Makefiles" \
    -DCMAKE_CXX_FLAGS=-fPIC \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=../../Resources \
    ..

# Build static library only (faster, avoids tool linking issues)
mingw32-make GEMS3K_STATIC -j4

# Install
mingw32-make install
```

**What this does:**
- Creates `build/` directory
- Runs CMake with `-G "MinGW Makefiles"`
- Compiles GEMS3K static library
- Installs to `../../Resources/` (i.e., `thames-hydration/src/Resources/`)

### 1.4 Verify Build Success

```bash
ls -la ../../Resources/lib/
```

Expected output:
```
libGEMS3K-static.a
libGEMS3K.dll (or similar)
```

---

## Step 2: Build THAMES-Hydration

THAMES-Hydration is the main hydration simulation engine.

### 2.1 Navigate to THAMES-Hydration Directory

```bash
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend/thames-hydration
```

### 2.2 Prepare Build Directory

```bash
# Clean previous build if exists
rm -rf build
mkdir build
cd build
```

### 2.3 Configure with CMake

```bash
cmake -G "MinGW Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    ..
```

**Expected output includes:**
```
-- Found GEMSK3K_LIB: [.../Resources/lib/libGEMS3K-static.a]
-- Found MATH_LIB: [...]
```

If GEMS3K is not found, Step 1 was not successful.

### 2.4 Build

```bash
mingw32-make -j4
```

### 2.5 Install

```bash
mingw32-make install
```

### 2.6 Verify Build

```bash
ls -la ../bin/
```

Expected output:
```
thames.exe
```

### 2.7 Copy to Application bin/

```bash
cp ../bin/thames.exe /c/Users/jwbullard/Desktop/foo/THAMES/bin/
```

---

## Step 3: Build Micgen

Micgen generates cement microstructures.

### 3.1 Navigate to Backend Directory

```bash
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend
```

### 3.2 Prepare Build Directory

```bash
rm -rf build
mkdir build
cd build
```

### 3.3 Configure with CMake

```bash
cmake -G "MinGW Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    ..
```

**Expected output includes:**
```
-- Found PNG: ...
-- Found ZLIB: ...
```

### 3.4 Build

```bash
mingw32-make -j4
```

### 3.5 Copy to Application bin/

```bash
cp micgen.exe /c/Users/jwbullard/Desktop/foo/THAMES/bin/
```

### 3.6 Verify

```bash
ls -la /c/Users/jwbullard/Desktop/foo/THAMES/bin/
```

Expected:
```
micgen.exe
thames.exe
```

---

## Verification

### Test Executables

```bash
# Test thames
/c/Users/jwbullard/Desktop/foo/THAMES/bin/thames.exe --help

# Test micgen
/c/Users/jwbullard/Desktop/foo/THAMES/bin/micgen.exe --help
```

### Check DLL Dependencies

If executables fail to run, they may need DLLs from MSYS2:

```bash
ldd /c/Users/jwbullard/Desktop/foo/THAMES/bin/thames.exe
ldd /c/Users/jwbullard/Desktop/foo/THAMES/bin/micgen.exe
```

Common required DLLs (usually found automatically if PATH includes MinGW):
- `libstdc++-6.dll`
- `libgcc_s_seh-1.dll`
- `libwinpthread-1.dll`
- `libpng16-16.dll`
- `zlib1.dll`

---

## Troubleshooting

### GCC 15 Compatibility: Missing `<cstdint>` Header

**Error:**
```
io_simdjson.h: error: 'int64_t' was not declared in this scope
```

**Cause:** GCC 15 removed implicit header includes that older versions had.

**Solution:** Edit `GEMS3K-standalone/GEMS3K/io_simdjson.h` and add `#include <cstdint>`:

```cpp
#include <fstream>
#include <vector>
#include <memory>
#include <cstdint>    // ADD THIS LINE
#include "verror.h"
```

**Note:** This fix has already been applied to the repository.

---

### ImageMagick Dependency Removed

As of December 2025, the THAMES C++ code no longer requires ImageMagick for PNG conversion.

**What was changed:**
- Added `PngWriter.h` utility class using native libpng
- Modified `Lattice.cc` and `ElasticModel.cc` to use `PngWriter::convertPpmToPng()`
- Added `find_package(PNG REQUIRED)` to CMakeLists.txt
- Movie frames are now saved as PNG instead of GIF (animation can be done in post-processing)

**Benefits:**
- No need to install ImageMagick on Windows
- Simpler deployment
- Smaller executable

---

### "cmake not found"

**Cause:** Not using MSYS2 MinGW 64-bit terminal

**Solution:** Open "MSYS2 MinGW 64-bit" from Start Menu, not regular command prompt or Git Bash.

### "GEMS3K library not found"

**Error:**
```
FATAL_ERROR: Did not find lib GEMS3K-static
```

**Solution:** Ensure Step 1 completed successfully. Check that `Resources/lib/libGEMS3K-static.a` exists.

### "PNG/ZLIB not found"

**Error:**
```
Could not find PNG
```

**Solution:** Install missing packages:
```bash
pacman -S mingw-w64-x86_64-libpng mingw-w64-x86_64-zlib
```

### "make: command not found"

**Solution:** Use `mingw32-make` instead of `make`:
```bash
mingw32-make -j4
```

Or install MSYS2 make:
```bash
pacman -S make
```

### Executable won't run (missing DLL)

**Solution:** Add MinGW bin to PATH:
```bash
export PATH="/c/msys64/mingw64/bin:$PATH"
```

Or copy required DLLs to the same directory as the executable.

### Build from scratch (clean rebuild)

```bash
# GEMS3K
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend/thames-hydration/src/GEMS3K-standalone
rm -rf build
rm -rf ../../Resources/lib/*

# THAMES-Hydration
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend/thames-hydration
rm -rf build
rm -rf bin/*

# Backend
cd /c/Users/jwbullard/Desktop/foo/THAMES/backend
rm -rf build

# Then rebuild in order: GEMS3K -> THAMES-Hydration -> Backend
```

---

## Quick Reference

### Complete Build Script

Save this as `build-all.sh` and run from MSYS2 MinGW 64-bit terminal:

```bash
#!/bin/bash
set -e  # Exit on error

THAMES_ROOT="/c/Users/jwbullard/Desktop/foo/THAMES"

echo "=== Building GEMS3K ==="
cd "$THAMES_ROOT/backend/thames-hydration/src/GEMS3K-standalone"
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" \
    -DCMAKE_CXX_FLAGS=-fPIC \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=../../Resources \
    ..
mingw32-make GEMS3K_STATIC -j4
mingw32-make install

echo "=== Building THAMES-Hydration ==="
cd "$THAMES_ROOT/backend/thames-hydration"
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
mingw32-make -j4
mingw32-make install
cp ../bin/thames.exe "$THAMES_ROOT/bin/"

echo "=== Building Micgen ==="
cd "$THAMES_ROOT/backend"
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
mingw32-make -j4
cp micgen.exe "$THAMES_ROOT/bin/"

echo "=== Build Complete ==="
ls -la "$THAMES_ROOT/bin/"
```

### Key Commands Summary

| Task | Command |
|------|---------|
| Open correct terminal | Start Menu -> MSYS2 MinGW 64-bit |
| Configure CMake | `cmake -G "MinGW Makefiles" ..` |
| Build | `mingw32-make -j4` |
| Install | `mingw32-make install` |
| Clean build | `rm -rf build && mkdir build` |
| Check package installed | `pacman -Q <package>` |
| Install package | `pacman -S <package>` |
| Check DLL dependencies | `ldd <executable>` |

### Directory Structure After Build

```
THAMES/
├── bin/
│   ├── thames.exe        <- Hydration simulator
│   └── micgen.exe        <- Microstructure generator
├── backend/
│   ├── build/            <- Micgen build output
│   └── thames-hydration/
│       ├── bin/
│       │   └── thames.exe
│       ├── build/        <- THAMES build output
│       ├── Resources/
│       │   └── lib/
│       │       └── libGEMS3K-static.a
│       └── src/
│           └── GEMS3K-standalone/
│               └── build/  <- GEMS3K build output
└── src/                  <- Python application
```

---

## Notes

- Always use the **MSYS2 MinGW 64-bit** terminal for building
- The `-j4` flag runs 4 parallel compile jobs; adjust based on your CPU cores
- CMake caches configuration; delete `build/` directory for a fresh start
- GEMS3K uses C++17; ensure GCC 14+ is installed

---

**Document prepared by:** THAMES Development Team
**Platform:** Windows 10/11 with MSYS2

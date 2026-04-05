#!/bin/bash
#
# Windows Build Script (MSYS2 MinGW-w64 + Clang)
# Builds: GEMS3K, THAMES-Hydration, micgen
# Usage: ./build-windows.sh [clean]
#   clean - removes build directories and rebuilds from scratch
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GEMS3K_DIR="$SCRIPT_DIR/backend/thames-hydration/src/GEMS3K-standalone"
THAMES_DIR="$SCRIPT_DIR/backend/thames-hydration"
MICGEN_DIR="$SCRIPT_DIR/backend"
BIN_DIR="$SCRIPT_DIR/bin"

CMAKE=/c/msys64/mingw64/bin/cmake.exe
MAKE=/c/msys64/mingw64/bin/mingw32-make.exe
CC=/c/msys64/mingw64/bin/clang.exe
CXX=/c/msys64/mingw64/bin/clang++.exe
CMAKE_COMMON="-G \"MinGW Makefiles\" -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX -DCMAKE_MAKE_PROGRAM=$MAKE"
JOBS=4

# Handle clean build
if [ "$1" = "clean" ]; then
    echo "=== Clean build requested ==="
    rm -rf "$GEMS3K_DIR/build"
    rm -rf "$THAMES_DIR/build"
    rm -rf "$MICGEN_DIR/build"
fi

echo "========================================="
echo "THAMES Windows Build (MSYS2 Clang)"
echo "========================================="

# Step 1: Build GEMS3K
echo ""
echo "--- Step 1/3: Building GEMS3K ---"
mkdir -p "$GEMS3K_DIR/build"
cd "$GEMS3K_DIR/build"
$CMAKE -G "MinGW Makefiles" \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DCMAKE_MAKE_PROGRAM=$MAKE \
    -DCMAKE_CXX_FLAGS=-fPIC \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=../../Resources \
    ..
# Build all targets; kva2json tool may fail to link (not needed) so we
# build the static library explicitly and continue past errors.
$MAKE -j$JOBS || true
$MAKE GEMS3K_STATIC || true
$MAKE install || true

# Verify the static library was actually produced
if [ ! -f "$GEMS3K_DIR/build/lib/libGEMS3K-static.a" ] && \
   [ ! -f "$GEMS3K_DIR/../Resources/lib/libGEMS3K-static.a" ]; then
    echo "ERROR: libGEMS3K-static.a was not built"
    exit 1
fi
echo "GEMS3K: OK"

# Step 2: Build THAMES-Hydration
echo ""
echo "--- Step 2/3: Building THAMES-Hydration ---"
mkdir -p "$THAMES_DIR/build"
cd "$THAMES_DIR/build"
$CMAKE -G "MinGW Makefiles" \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DCMAKE_MAKE_PROGRAM=$MAKE \
    -DCMAKE_BUILD_TYPE=Release \
    ..
$MAKE -j$JOBS
echo "THAMES: OK"

# Step 3: Build micgen
echo ""
echo "--- Step 3/3: Building micgen ---"
mkdir -p "$MICGEN_DIR/build"
cd "$MICGEN_DIR/build"
$CMAKE -G "MinGW Makefiles" \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DCMAKE_MAKE_PROGRAM=$MAKE \
    -DCMAKE_BUILD_TYPE=Release \
    ..
# Build micgen target specifically (zlib shared DLL resource compilation
# may fail on MSYS2 but micgen only needs zlibstatic)
$MAKE -j$JOBS micgen
echo "micgen: OK"

# Step 4: Install to bin/
echo ""
echo "--- Installing to bin/ ---"
mkdir -p "$BIN_DIR"
cp "$THAMES_DIR/build/thames.exe" "$BIN_DIR/thames.exe"
cp "$MICGEN_DIR/build/micgen.exe" "$BIN_DIR/micgen.exe"

# Ensure libpng DLL is present
if [ ! -f "$BIN_DIR/libpng16-16.dll" ]; then
    if [ -f "/c/msys64/mingw64/bin/libpng16-16.dll" ]; then
        cp /c/msys64/mingw64/bin/libpng16-16.dll "$BIN_DIR/"
        echo "Copied libpng16-16.dll to bin/"
    else
        echo "WARNING: libpng16-16.dll not found in MSYS2"
    fi
fi

echo ""
echo "========================================="
echo "Build complete!"
echo "========================================="
echo "  bin/thames.exe  - $(ls -lh "$BIN_DIR/thames.exe" | awk '{print $5}')"
echo "  bin/micgen.exe   - $(ls -lh "$BIN_DIR/micgen.exe" | awk '{print $5}')"
echo ""

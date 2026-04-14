#!/bin/bash
#
# macOS Build Script
# Builds: GEMS3K, THAMES-Hydration, micgen
# Usage: ./build-macos.sh [clean]
#   clean - removes build directories and rebuilds from scratch
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GEMS3K_DIR="$SCRIPT_DIR/backend/thames-hydration/src/GEMS3K-standalone"
THAMES_DIR="$SCRIPT_DIR/backend/thames-hydration"
MICGEN_DIR="$SCRIPT_DIR/backend"
BIN_DIR="$SCRIPT_DIR/bin"

JOBS=4

# Handle clean build
if [ "$1" = "clean" ]; then
    echo "=== Clean build requested ==="
    rm -rf "$GEMS3K_DIR/build"
    rm -rf "$THAMES_DIR/build"
    rm -rf "$MICGEN_DIR/build"
fi

echo "========================================="
echo "THAMES macOS Build"
echo "========================================="

# Step 1: Build GEMS3K
echo ""
echo "--- Step 1/3: Building GEMS3K ---"
mkdir -p "$GEMS3K_DIR/build"
cd "$GEMS3K_DIR/build"
cmake .. \
    -DCMAKE_CXX_FLAGS=-fPIC \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=../../Resources
# Build libraries first to avoid kva2json link race condition
make -j$JOBS GEMS3K_STATIC GEMS3K_SHARED
make -j$JOBS
make install
echo "GEMS3K: OK"

# Step 2: Build THAMES-Hydration
echo ""
echo "--- Step 2/3: Building THAMES-Hydration ---"
mkdir -p "$THAMES_DIR/build"
cd "$THAMES_DIR/build"
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$JOBS
echo "THAMES: OK"

# Step 3: Build micgen
echo ""
echo "--- Step 3/3: Building micgen ---"
mkdir -p "$MICGEN_DIR/build"
cd "$MICGEN_DIR/build"
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$JOBS
echo "micgen: OK"

# Step 4: Install to bin/
echo ""
echo "--- Installing to bin/ ---"
mkdir -p "$BIN_DIR"
cp "$THAMES_DIR/build/thames" "$BIN_DIR/thames"
cp "$MICGEN_DIR/build/micgen" "$BIN_DIR/micgen"

echo ""
echo "========================================="
echo "Build complete!"
echo "========================================="
echo "  bin/thames  - $(ls -lh "$BIN_DIR/thames" | awk '{print $5}')"
echo "  bin/micgen  - $(ls -lh "$BIN_DIR/micgen" | awk '{print $5}')"
echo ""

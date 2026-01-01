# Session 21 Summary: Windows Clang Build & Platform Compatibility Fixes

**Date:** December 31, 2025
**Platform:** Windows 10 with MSYS2 MinGW-w64 + Clang 21.1.1

## Overview

This session resolved the Windows crash issue that was identified in Session 20. The root cause was a combination of compiler differences and platform-specific integer sizes.

## Key Accomplishments

### 1. Clang Compiler Installation and Build

Installed Clang 21.1.1 on Windows via MSYS2:
```bash
pacman -S mingw-w64-x86_64-clang
```

Full build command for THAMES:
```bash
/c/msys64/mingw64/bin/cmake -G "MinGW Makefiles" \
  -DCMAKE_C_COMPILER=/c/msys64/mingw64/bin/clang.exe \
  -DCMAKE_CXX_COMPILER=/c/msys64/mingw64/bin/clang++.exe \
  -DCMAKE_MAKE_PROGRAM=/c/msys64/mingw64/bin/mingw32-make.exe ..
```

**Important:** Both GEMS3K and THAMES must be rebuilt with the same compiler to avoid linker errors.

### 2. Platform-Specific Integer Size Fix

**Root Cause:** `long int` is 64-bit on macOS but only 32-bit on Windows.

When summing wmc values across 60,000+ sites with individual values of ~1-2 million, the sum exceeded 2^31 (~2 billion), causing integer overflow on Windows.

**Fix:** Changed `long int` to `long long int` in Lattice.cc:
- Line 1245: `affSumInt`
- Line 2197: `wAffSumInt, vAffSumInt`
- Lines 2642, 6168: `sumWmcInt`
- Line 6297: `sumWmcT`

**Platform Behavior:**
| Type | macOS | Windows |
|------|-------|---------|
| `long int` | 64-bit | 32-bit |
| `long long int` | 64-bit | 64-bit |

### 3. Uninitialized Variable Fix

Added initialization in Site.cc constructors:
```cpp
wmc_ = 0;
wmc0_ = 0;
```

Both the default constructor and the overloaded constructor were missing these initializations.

### 4. Missing DLL Fix

Copied `libpng16-16.dll` from `/c/msys64/mingw64/bin/` to `bin/` folder. Required because PngWriter.h (added in Session 20) uses libpng.

### 5. Git LFS Migration

The `particle_shape_set.tar.gz` file (266 MB) exceeded GitHub's 100 MB limit. Migrated to Git LFS:
```bash
git stash --include-untracked
git lfs migrate import --include="*.tar.gz" --everything
git stash pop
git push --force-with-lease origin main
```

## Files Modified

1. **backend/thames-hydration/src/thameslib/Site.cc**
   - Added `wmc_ = 0;` and `wmc0_ = 0;` to both constructors

2. **backend/thames-hydration/src/thameslib/Lattice.cc**
   - Changed 4 instances of `long int` to `long long int`

3. **bin/libpng16-16.dll**
   - Copied from MSYS2 mingw64/bin

## Test Results

Hydration simulation ran successfully through 110+ cycles (400+ hours of simulated time out of 720 target).

## Git Status

- Repository successfully pushed to remote with Git LFS
- Large file `particle_shape_set.tar.gz` stored in LFS

## Lessons Learned

1. **Always use `long long int` for large accumulator variables** that may exceed 32-bit range on Windows
2. **Rebuild both GEMS3K and THAMES** when changing compilers - they share source files
3. **Initialize all member variables** in constructors to avoid undefined behavior
4. **Git LFS is required** for files over 100 MB on GitHub

## Next Steps

- Test the Mac build with the new changes (should be compatible)
- Consider adding automated tests for platform-specific issues
- Monitor hydration simulation to completion

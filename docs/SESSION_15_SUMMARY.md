# Session 15: Unified X-Fastest Voxel Ordering
December 18, 2025

## Overview

This session resolved a long-standing voxel ordering convention mismatch between micgen.c (which used Z-fastest ordering) and THAMES C++ code (which uses X-fastest ordering). All C and Python code was unified to use the X-fastest convention, which also matches VTK/PyVista expectations.

## Problem Statement

The user noticed that micgen.c and THAMES Lattice.cc used opposite loop nesting conventions:

- **micgen.c (old)**: X-outer, Y-middle, Z-inner loops → Z varies fastest in file
- **THAMES C++**: Z-outer, Y-middle, X-inner loops → X varies fastest in file

Despite this apparent mismatch, the system produced visually correct results. Investigation revealed that file bytes pass through THAMES unchanged (sequential read/write), preserving topology even though coordinate labels would be incorrect.

## Key Terminology

- **Innermost loop**: The variable that varies fastest in memory/file
- **Loop order**: `for z { for y { for x { }}}` means X is innermost (X-fastest)
- **Index formula**:
  - X-fastest: `index = x + xsize*y + xsize*ysize*z`
  - Z-fastest: `index = x*ysize*zsize + y*zsize + z`

## Technical Investigation

### Empirical Evidence

The user created a 110×100×100 microstructure with aggregate slab (phase 8) confined to the last 10 X-slices (x = 100-109). By examining both micgen output and THAMES hydration output:

- With the **old** Z-fastest convention in micgen.c:
  - Expected aggregate start: line 1,000,006 (voxel at x=100, y=0, z=0)
  - Actual aggregate start: line 540,006

- Line 540,006 corresponds to position (x=5, y=40, z=0) in Z-fastest indexing, BUT (x=5, y=40, z=99) in X-fastest indexing

This proved that THAMES was interpreting the file with X-fastest indexing while micgen wrote with Z-fastest indexing. The bytes passed through unchanged, but the coordinate interpretation was wrong.

### Why It Worked Anyway

1. **Topology preservation**: Neighboring voxels in the file remain neighbors regardless of coordinate labels
2. **Hydration chemistry**: Works on local neighborhoods, not absolute coordinates
3. **Isotropic properties**: For cubic/near-cubic systems, results appear correct even with swapped dimensions

## Solution: Unified X-Fastest Convention

We chose X-fastest because:
1. Matches THAMES C++ convention (no changes needed there)
2. Matches VTK/PyVista expectations (Fortran-style ordering)
3. More intuitive for visualization (X varies fastest like image raster order)

## Files Modified

### C Code

#### backend/src/thamesauxlib/memutil.c (lines 992-999)
Core index function used throughout C codebase:
```c
size_t getInt3dindex(Int3d thing, size_t x, size_t y, size_t z) {
  /* X-fastest ordering (matches THAMES C++ convention) */
  /* Index formula: x + xsize*y + xsize*ysize*z */
  return (x + (thing.xsize * y) + (thing.xsize * thing.ysize * z));
}
```

#### backend/src/micgen.c (lines 4186-4207)
Changed file writing loop order from X-outer/Z-inner to Z-outer/X-inner:
```c
for (iz = 0; iz < Zsyssize; iz++) {
  for (iy = 0; iy < Ysyssize; iy++) {
    for (ix = 0; ix < Xsyssize; ix++) {
      valout = Cemreal.val[getInt3dindex(Cemreal, ix, iy, iz)];
      fprintf(outfile, "\n%d", valout);
      // ... histogram updates
    }
  }
}
```

### Python Code

#### src/app/services/phase_id_mapping_service.py (lines 586-617)
- Changed reshape from `(x_size, y_size, z_size)` to `(z_size, y_size, x_size)`
- Changed write loop from X-outer/Z-inner to Z-outer/X-inner

#### src/app/windows/panels/microstructure_panel.py (line 715)
```python
# Reshape to (z, y, x) so X varies fastest with C-order
voxel_data = voxel_data.reshape((z_size, y_size, x_size))
```

#### src/app/windows/dialogs/pyvista_strain_viewer.py (line 503)
```python
# Reshape to (z, y, x) for X-fastest with C-order
self.strain_data = np.array(data_values).reshape(z_dim, y_dim, x_dim)
```

#### src/app/visualization/pyvista_3d_viewer.py (multiple locations)
- Fixed VTK SetDimensions (lines 841-848): Extract (nz, ny, nx) from shape, pass (nx, ny, nz) to VTK
- Fixed volume_bounds (lines 745-752): Correctly map shape to X/Y/Z bounds
- Fixed 4 file export functions for stat3d/perc3d (lines 1265-1273, 1365-1373, 1475-1483, 1571-1579)

## NumPy/VTK Convention Notes

### NumPy Reshape with C-Order
When using `array.reshape((a, b, c))` with default C-order:
- Last dimension (c) varies fastest
- First dimension (a) varies slowest

For X-fastest file ordering:
- Reshape to `(z_size, y_size, x_size)` → X varies fastest ✓

### VTK ImageData
VTK expects dimensions as (nx, ny, nz) but stores data with X-fastest ordering (Fortran-style).
- Array shape: `(nz, ny, nx)` (Python notation)
- VTK SetDimensions: `(nx, ny, nz)` (VTK notation)

## Testing Results

The user tested 4 combinations:

| Test Case | Aggregate Slab | Long Dimension | Result |
|-----------|---------------|----------------|--------|
| 1 | Yes | X (110×100×100) | ✓ Pass |
| 2 | Yes | Z (100×100×110) | ✓ Pass |
| 3 | No | X (110×100×100) | ✓ Pass |
| 4 | No | Z (100×100×110) | ✓ Pass |

All tests verified:
- Microstructure generation (micgen)
- 3D visualization (PyVista)
- THAMES hydration simulation
- Elastic moduli calculation

## Git Commits This Session

1. **Pre-change baseline**: "Session 15: Pre-voxel-ordering baseline"
   - Created before making any changes for safety

2. **Implementation commit**: (pending with this summary)
   - All voxel ordering unification changes

## Pending Items

1. **Add progress tracking for Elastic Moduli operations** - THAMES C++ side needs implementation
2. **Fix small glitches in 3D visualization functionality** - User reported minor issues
3. **Consider applying same fix to VCCTL project** - Uses same Z-fastest convention in old code

## Critical Files for Next Session

- **C Code**: `backend/src/thamesauxlib/memutil.c`, `backend/src/micgen.c`
- **Python Services**: `src/app/services/phase_id_mapping_service.py`
- **Visualization**: `src/app/visualization/pyvista_3d_viewer.py`
- **Panels**: `src/app/windows/panels/microstructure_panel.py`
- **Dialogs**: `src/app/windows/dialogs/pyvista_strain_viewer.py`

## Lessons Learned

1. **Always verify empirically**: Despite code analysis suggesting a mismatch, the system appeared to work. Only careful byte-level analysis revealed the actual behavior.

2. **Topology vs. coordinates**: Hydration simulations work on neighbor relationships, which are preserved regardless of coordinate labeling. This can mask indexing bugs.

3. **Unified conventions matter**: Having consistent conventions across C and Python code eliminates subtle bugs and makes maintenance easier.

4. **VTK expectations**: VTK/PyVista expect X-fastest ordering, making it the natural choice for visualization applications.

# Session 18: Strain Energy Visualization & 3D Orientation Axes

**Date:** December 26, 2025
**Platform:** macOS 26.2 (Darwin 25.2.0)

## Overview

This session focused on two main visualization enhancements:
1. Adding a coordinate axis orientation indicator to the 3D microstructure viewer
2. Implementing strain energy visualization now that THAMES C++ outputs `energy.img` files

Additionally, this session includes comprehensive analysis and preparation for Windows migration.

---

## 3D Orientation Axes Indicator

### Problem Statement

The 3D microstructure viewer lacked visual feedback for orientation. When rotating the view, users couldn't tell which direction was X, Y, or Z without reference points.

### Solution Implemented

Created a corner viewport with synchronized orientation axes that rotate with the main view.

### Implementation Details

**File:** `src/app/visualization/pyvista_3d_viewer.py`

**New Method: `_create_orientation_axes_renderer()`**
```python
def _create_orientation_axes_renderer(self):
    """Create a small renderer in the corner showing orientation axes."""
    self.axes_renderer = vtkRenderer()
    self.axes_renderer.SetBackground(0.95, 0.95, 0.95)
    self.axes_renderer.SetViewport(0.0, 0.0, 0.20, 0.20)  # Bottom-left 20%

    self.orientation_axes = vtkAxesActor()
    self.orientation_axes.SetTotalLength(1.5, 1.5, 1.5)
    self.orientation_axes.SetShaftType(0)  # Cylinder shafts
    self.orientation_axes.SetCylinderRadius(0.04)
    self.orientation_axes.SetConeRadius(0.35)  # Large arrowheads
    self.orientation_axes.SetConeResolution(20)
    self.orientation_axes.SetNormalizedShaftLength(0.7, 0.7, 0.7)
    self.orientation_axes.SetNormalizedTipLength(0.3, 0.3, 0.3)
    self.orientation_axes.SetNormalizedLabelPosition(1.3, 1.3, 1.3)  # Labels away from tips

    # Configure axis labels
    for axis_label in [self.orientation_axes.GetXAxisCaptionActor2D(),
                       self.orientation_axes.GetYAxisCaptionActor2D(),
                       self.orientation_axes.GetZAxisCaptionActor2D()]:
        text_prop = axis_label.GetCaptionTextProperty()
        text_prop.SetFontSize(24)
        text_prop.SetBold(True)
        text_prop.SetShadow(True)

    # Set axis colors (RGB for XYZ)
    self.orientation_axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 0, 0)
    self.orientation_axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0.8, 0)
    self.orientation_axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 1)

    # Camera setup - zoomed out to fit labels
    self.axes_camera = vtkCamera()
    self.axes_camera.SetPosition(5, 5, 5)
    self.axes_camera.SetFocalPoint(0, 0, 0)
    self.axes_camera.SetViewUp(0, 1, 0)
    self.axes_renderer.SetActiveCamera(self.axes_camera)
    self.axes_renderer.ResetCamera()
    self.axes_camera.Zoom(0.6)  # Zoom out to prevent label clipping
```

**New Method: `_sync_axes_camera()`**
```python
def _sync_axes_camera(self):
    """Synchronize axes camera orientation with main camera."""
    if not hasattr(self, 'axes_camera') or not hasattr(self, 'camera'):
        return

    position = list(self.camera.GetPosition())
    focal = list(self.camera.GetFocalPoint())
    view_up = list(self.camera.GetViewUp())

    # Calculate direction vector
    direction = [focal[i] - position[i] for i in range(3)]
    norm = math.sqrt(sum(d*d for d in direction))
    if norm > 0:
        direction = [d/norm for d in direction]

    # Set axes camera at fixed distance in same direction
    distance = 8.0
    self.axes_camera.SetPosition([-d * distance for d in direction])
    self.axes_camera.SetFocalPoint(0, 0, 0)
    self.axes_camera.SetViewUp(view_up)
```

**Integration:** `_sync_axes_camera()` is called in `_render_to_gtk()` before rendering.

### Issues Encountered and Solutions

| Issue | Solution |
|-------|----------|
| Arrowheads too small | Increased `SetConeRadius(0.35)` and `SetNormalizedTipLength(0.3)` |
| Labels overlapping arrowheads | Added `SetNormalizedLabelPosition(1.3, 1.3, 1.3)` |
| Y label clipped at top | Reduced camera zoom to 0.6, increased sync distance to 8.0 |

---

## Strain Energy Visualization

### Problem Statement

After Session 17, the strain energy button was non-functional because THAMES C++ wasn't outputting strain energy data. The user has now implemented `energy.img` output in the C++ code.

### Solution Implemented

Complete rewrite of `pyvista_strain_viewer.py` to use VTK directly (matching the main viewer architecture) and updated file discovery for THAMES format.

### Implementation Details

**File:** `src/app/windows/dialogs/pyvista_strain_viewer.py`

**Updated Imports:**
```python
from vtkmodules.vtkCommonDataModel import vtkImageData, vtkDataObject
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkThreshold, vtkGlyph3D
from vtkmodules.vtkFiltersGeneral import vtkVertexGlyphFilter
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.util import numpy_support
```

**THAMES Header Parsing:**
```python
if line.startswith('#THAMES:'):
    line = line[8:].strip()  # Remove "#THAMES:" prefix
```

**VTK Visualization Pipeline:**
```python
def _create_pyvista_volume(self, data, x_size, y_size, z_size, resolution):
    # Create VTK image data
    image_data = vtkImageData()
    image_data.SetDimensions(x_size, y_size, z_size)
    image_data.SetSpacing(resolution, resolution, resolution)

    # Add scalar array
    vtk_array = numpy_support.numpy_to_vtk(data.ravel(order='C'))
    vtk_array.SetName("StrainEnergy")
    image_data.GetPointData().SetScalars(vtk_array)

    # Create threshold filter
    threshold = vtkThreshold()
    threshold.SetInputData(image_data)
    threshold.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "StrainEnergy")
    threshold.SetLowerThreshold(min_val + 0.5 * (max_val - min_val))

    # Create cube glyph for each voxel
    cube = vtkCubeSource()
    cube.SetXLength(resolution * 0.95)
    cube.SetYLength(resolution * 0.95)
    cube.SetZLength(resolution * 0.95)

    glyph = vtkGlyph3D()
    glyph.SetInputConnection(threshold.GetOutputPort())
    glyph.SetSourceConnection(cube.GetOutputPort())
    glyph.SetScaleModeToDataScalingOff()

    # Apply colormap via lookup table
    lut = vtkLookupTable()
    lut.SetNumberOfColors(256)
    lut.SetHueRange(0.667, 0.0)  # Blue to red (jet)
    lut.SetRange(min_val, max_val)
    lut.Build()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(glyph.GetOutputPort())
    mapper.SetLookupTable(lut)
    mapper.SetScalarRange(min_val, max_val)
```

**Hide Phase Controls for Strain Energy:**
```python
# In _create_widgets():
if hasattr(self.pyvista_viewer, 'phase_control_panel'):
    self.pyvista_viewer.phase_control_panel.hide()
    self.pyvista_viewer.phase_control_panel.set_no_show_all(True)
```

**File:** `src/app/windows/panels/results_panel.py`

**THAMES File Discovery:**
```python
def _has_strain_energy(self, folder_path):
    # Check for energy.img in Result/ subdirectory (THAMES format)
    test_file = folder_path / "Result" / "energy.img"
    if test_file.exists():
        return True
    # Fallback to VCCTL format
    return (folder_path / "energy.img").exists()
```

### Issues Encountered and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "PyVista plotter not available" | Main viewer uses VTK `renderer`, not PyVista `plotter` | Rewrote to check for `renderer` attribute |
| `numpy_support` not defined | Import was in try/except block | Moved import outside try block |
| `vtkLookupTable` import error | Wrong module (`vtkRenderingCore`) | Changed to `vtkCommonCore` |
| Colors identical everywhere | Using isosurface contours (single color per level) | Switched to voxel cubes with scalar coloring |
| No visualization appearing | Threshold range too narrow (0-2%) | Increased default to 50% |

---

## Files Modified

| File | Changes |
|------|---------|
| `src/app/visualization/pyvista_3d_viewer.py` | Added `_create_orientation_axes_renderer()`, `_sync_axes_camera()`, integrated into render loop |
| `src/app/windows/dialogs/pyvista_strain_viewer.py` | Complete VTK rewrite, THAMES header support, hidden phase controls |
| `src/app/windows/panels/results_panel.py` | THAMES `Result/energy.img` file discovery |

---

## Testing Results

### Orientation Axes
- Axes display in bottom-left corner (20% viewport)
- Labels clearly visible (X=red, Y=green, Z=blue)
- Arrowheads properly sized and visible
- Rotation synchronized with main view in real-time
- No clipping of labels at any orientation

### Strain Energy Visualization
- Energy data loads from `Result/energy.img`
- THAMES header format (`#THAMES:`) parsed correctly
- Threshold slider adjusts visualization
- Colormap selection works (jet, viridis, coolwarm, plasma, magma)
- Phase controls hidden (irrelevant for strain energy)
- Min/max sliders correctly bound values

---

## Windows Migration Analysis

### High-Risk Components

#### 1. VTK/PyVista Integration
**Risk Level:** HIGH

**Concerns:**
- VTK module import paths may differ between platforms
- Headless rendering initialization may require different flags
- `vtkmodules.vtkCommonCore` vs `vtkmodules.vtkRenderingCore` organization

**Mitigation:**
- Create a simple VTK test script to verify imports on Windows
- Test offscreen rendering before GTK integration
- Consider `vtk-osmesa` wheel if GPU acceleration issues occur

#### 2. Path Handling
**Risk Level:** MEDIUM

**Concerns:**
- THAMES uses `Result/` subdirectory (forward slash)
- Windows uses backslash natively
- `pathlib.Path` should handle this, but verify

**Files to Check:**
- `results_panel.py` - `Result/energy.img` path
- `pyvista_strain_viewer.py` - file path construction
- `hydration_results_viewer.py` - `Result/` subdirectory discovery

**Mitigation:**
- Audit all path construction to use `pathlib.Path` / operator
- Never use string concatenation with `/` or `\`

#### 3. File Header Parsing
**Risk Level:** LOW

**Concerns:**
- Windows uses `\r\n` line endings
- macOS uses `\n` line endings
- `#THAMES:` prefix parsing uses string slicing

**Current Status:** Code uses `.strip()` which handles both line endings.

#### 4. subprocess Flags
**Risk Level:** MEDIUM

**Concerns:**
- Windows spawns console windows without `CREATE_NO_WINDOW`
- macOS doesn't need any special flags

**Pattern to Apply:**
```python
popen_kwargs = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}
if sys.platform == 'win32':
    popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
process = subprocess.Popen(cmd, **popen_kwargs)
```

**Files to Check:**
- Any file using `subprocess.Popen` or `subprocess.run`

### Pre-Windows Migration Checklist

```
[ ] Python/pip environment setup (MSYS2/MinGW)
[ ] PyGObject installation verification
[ ] VTK installation and import test
[ ] GTK3 rendering test
[ ] VTK + GTK integration test (offscreen render to widget)
[ ] pathlib.Path audit (no hardcoded slashes)
[ ] subprocess flags audit
[ ] .img file reading with Windows line endings
[ ] THAMES C++ executables compiled for Windows
[ ] PyInstaller .spec file creation/adaptation
```

### Known Windows Issues from VCCTL Experience

1. **PyGObject Installation**
   - Requires MSYS2/MinGW environment
   - Cannot use regular pip on Windows

2. **VTK Wheel Selection**
   - Standard `vtk` wheel may have GPU issues
   - Consider `vtk-osmesa` for software rendering

3. **PyInstaller Bundling**
   - Significantly different from macOS
   - Hidden imports may differ
   - DLL dependencies must be included

4. **Console Window Spawning**
   - All subprocess calls spawn visible console
   - Must add `CREATE_NO_WINDOW` flag everywhere

---

## Session Statistics

- **Duration:** ~2 hours
- **Files Modified:** 3
- **Lines Added:** ~200
- **Key Features:** Orientation axes, strain energy visualization
- **Platform:** macOS (Windows analysis only)

---

## Next Steps

1. **Windows Development Session**
   - Set up Windows development environment
   - Follow pre-migration checklist
   - Test VTK integration first (highest risk)

2. **Potential Enhancements**
   - Add strain energy statistics (min, max, mean, std)
   - Add export to CSV for strain energy data
   - Color scale bar for strain energy values

3. **Known Issues**
   - None identified for macOS
   - Windows compatibility untested

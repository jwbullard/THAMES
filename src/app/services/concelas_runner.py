#!/usr/bin/env python3
"""
Concelas Runner — glue between THAMES C++ elastic output and concelas_service.

Responsibilities:
- Parse EffectiveModuli.csv (paste moduli) and ITZModuli.csv (per-layer K, G)
  produced by `thames -s 5` in ELASTIC_CALC mode.
- Parse cement PSD and aggregate grading CSV files.
- Call concelas_service.run_concelas() with the assembled inputs.
- Append concrete-scale rows to EffectiveModuli.csv in the same format the
  C++ code uses (Property,Value,Units).
- Write ConcelasLog.txt for debugging.

Pure algorithms live in concelas_service.py. File I/O lives here.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.services.concelas_service import (
    AggregateSource,
    ConcelasResult,
    run_concelas,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConcelasRunnerError(Exception):
    """Raised when concelas post-processing cannot be completed."""


class MissingInputError(ConcelasRunnerError):
    """A required input file (CSV / PSD / grading) was not found."""


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------


@dataclass
class PasteModuli:
    """Paste-scale effective moduli read from EffectiveModuli.csv."""

    bulk_gpa: float
    shear_gpa: float
    young_gpa: float
    poisson: float
    resolution_um: float
    nx: int
    ny: int
    nz: int
    microstructure_name: str


@dataclass
class LayerProfile:
    """Per-layer ITZ-to-bulk paste profile read from ITZModuli.csv."""

    layer_k_gpa: List[float]
    layer_g_gpa: List[float]
    layer_distance_um: List[float]
    resolution_um: float
    nx: int


def _parse_property_csv(path: Path) -> List[Tuple[str, str, str]]:
    """Parse a Property,Value,Units CSV into a list of 3-tuples.

    Tolerates:
    - Leading/trailing whitespace around any field (the C++ code writes
      "Resolution, " with a trailing space in EffectiveModuli.csv).
    - Empty lines and comment lines.
    - Missing trailing Units column.
    """
    rows: List[Tuple[str, str, str]] = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for raw in reader:
            if not raw:
                continue
            fields = [cell.strip() for cell in raw]
            # Skip header row
            if len(fields) >= 1 and fields[0].lower() == "property":
                continue
            # Pad to 3 columns if trailing units is missing
            while len(fields) < 3:
                fields.append("")
            rows.append((fields[0], fields[1], fields[2]))
    return rows


def read_effective_moduli(path: Path) -> PasteModuli:
    """Parse EffectiveModuli.csv written by thames -s 5.

    Raises MissingInputError if the file is absent or malformed.
    """
    if not path.exists():
        raise MissingInputError(f"EffectiveModuli.csv not found at {path}")

    values: Dict[str, str] = {}
    for prop, val, _units in _parse_property_csv(path):
        values[prop] = val

    try:
        return PasteModuli(
            bulk_gpa=float(values["Bulk_modulus"]),
            shear_gpa=float(values["Shear_modulus"]),
            young_gpa=float(values["Youngs_modulus"]),
            poisson=float(values["Poissons_ratio"]),
            resolution_um=float(values["Resolution"]),
            nx=int(float(values["X_Dimension"])),
            ny=int(float(values["Y_Dimension"])),
            nz=int(float(values["Z_Dimension"])),
            microstructure_name=values.get("Microstructure", ""),
        )
    except (KeyError, ValueError) as exc:
        raise ConcelasRunnerError(
            f"EffectiveModuli.csv at {path} is missing or malformed: {exc}"
        ) from exc


_LAYER_KEY_RE = re.compile(r"^Layer_(-?\d+)_(distance|Bulk_modulus|Shear_modulus|Youngs_modulus|Poissons_ratio)$")


def read_itz_moduli(path: Path) -> LayerProfile:
    """Parse ITZModuli.csv written by thames -s 5.

    The C++ writer emits rows with labels ``Layer_<N>_<property>`` where
    <N> is a signed integer from the `i_inverse = i - aggX + 2` formula.
    We reassemble per-layer records keyed by <N>, then sort by the
    `distance` field so the resulting arrays run from the aggregate
    surface outward (smallest distance first).
    """
    if not path.exists():
        raise MissingInputError(f"ITZModuli.csv not found at {path}")

    header: Dict[str, str] = {}
    layers: Dict[int, Dict[str, float]] = {}

    for prop, val, _units in _parse_property_csv(path):
        m = _LAYER_KEY_RE.match(prop)
        if not m:
            header[prop] = val
            continue
        idx = int(m.group(1))
        field = m.group(2)
        try:
            layers.setdefault(idx, {})[field] = float(val)
        except ValueError:
            continue

    # Sort layers by distance from the aggregate surface
    ordered = sorted(layers.values(), key=lambda d: d.get("distance", 0.0))

    layer_k = [d.get("Bulk_modulus", 0.0) for d in ordered]
    layer_g = [d.get("Shear_modulus", 0.0) for d in ordered]
    layer_d = [d.get("distance", 0.0) for d in ordered]

    try:
        return LayerProfile(
            layer_k_gpa=layer_k,
            layer_g_gpa=layer_g,
            layer_distance_um=layer_d,
            resolution_um=float(header["Resolution"]),
            nx=int(float(header["X_Dimension"])),
        )
    except (KeyError, ValueError) as exc:
        raise ConcelasRunnerError(
            f"ITZModuli.csv at {path} is missing required header: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# PSD and grading file parsing
# ---------------------------------------------------------------------------


def read_cement_psd(path: Path) -> List[Tuple[float, float]]:
    """Read a cement PSD CSV into (diameter_um, volume_fraction) pairs.

    Format (VCCTL-style):
        <header line>
        <diameter_um>,<volume_fraction>
        <diameter_um>,<volume_fraction>
        ...

    The header line is discarded. Whitespace is tolerated.
    Returns an empty list if the file is missing so the caller can
    fall back to the default median diameter.
    """
    if not path.exists():
        logger.warning("Cement PSD file not found at %s; using default median", path)
        return []

    points: List[Tuple[float, float]] = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Detect and skip header (first row with non-numeric first cell)
    start_idx = 0
    if rows:
        first = rows[0][0].strip() if rows[0] else ""
        try:
            float(first)
        except ValueError:
            start_idx = 1

    for row in rows[start_idx:]:
        if len(row) < 2:
            continue
        try:
            diameter = float(row[0].strip())
            vol_frac = float(row[1].strip())
        except ValueError:
            continue
        points.append((diameter, vol_frac))

    return points


def read_grading_file(path: Path) -> List[Tuple[float, float]]:
    """Read an aggregate grading CSV into (sieve_opening_mm, mass_fraction) pairs.

    Same format as cement PSD. Header line is discarded. Returns empty
    list if the file is missing; the caller should treat that as "no
    aggregate of this type" and skip the corresponding AggregateSource.
    """
    return read_cement_psd(path)  # identical format


# ---------------------------------------------------------------------------
# Result appending
# ---------------------------------------------------------------------------


_CONCRETE_ROWS: Tuple[Tuple[str, str, str], ...] = (
    # (property_name, format_string, units)
    ("Concrete_aggregate_vf", "{aggregate_volume_fraction:.4f}", ""),
    ("Concrete_air_vf", "{air_volume_fraction:.4f}", ""),
    ("Concrete_matrix_vf", "{matrix_volume_fraction:.4f}", ""),
    ("Concrete_bulk_modulus", "{concrete_bulk_gpa:.4f}", "GPa"),
    ("Concrete_shear_modulus", "{concrete_shear_gpa:.4f}", "GPa"),
    ("Concrete_Youngs_modulus", "{concrete_young_gpa:.4f}", "GPa"),
    ("Concrete_Poissons_ratio", "{concrete_poisson:.4f}", ""),
    ("ITZ_bulk_modulus", "{itz_bulk_gpa:.4f}", "GPa"),
    ("ITZ_shear_modulus", "{itz_shear_gpa:.4f}", "GPa"),
    ("ITZ_width", "{itz_width_um:.3f}", "um"),
    ("Mortar_cube_strength", "{mortar_cube_strength_mpa:.4f}", "MPa"),
    ("Concrete_cube_strength", "{concrete_cube_strength_mpa:.4f}", "MPa"),
    ("Concrete_cylinder_strength", "{cylinder_strength_mpa:.4f}", "MPa"),
)


def append_concrete_rows(effective_moduli_csv: Path, result: ConcelasResult) -> None:
    """Append concrete-scale rows to an existing EffectiveModuli.csv.

    Uses the same Property,Value,Units format the C++ code writes.
    If any of the concrete keys already exist in the file, this call
    is a no-op (idempotent) to avoid duplicate rows from re-runs.
    """
    if not effective_moduli_csv.exists():
        raise MissingInputError(
            f"Cannot append concrete rows: {effective_moduli_csv} does not exist"
        )

    existing_props = {prop for prop, _v, _u in _parse_property_csv(effective_moduli_csv)}
    if any(row[0] in existing_props for row in _CONCRETE_ROWS):
        logger.info("Concrete rows already present in %s; skipping append",
                    effective_moduli_csv)
        return

    # Ensure the existing file ends with a newline before appending
    content = effective_moduli_csv.read_text()
    needs_newline = not content.endswith("\n")

    with effective_moduli_csv.open("a", newline="") as f:
        if needs_newline:
            f.write("\n")
        writer = csv.writer(f)
        for prop, fmt, units in _CONCRETE_ROWS:
            writer.writerow([prop, fmt.format(**result.__dict__), units])


def write_concelas_log(log_path: Path, result: ConcelasResult) -> None:
    """Write the per-run concelas log to a plain-text file for debugging."""
    log_path.write_text("\n".join(result.log_lines) + "\n")


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def run_and_append(
    elastic_output_dir: Path,
    fine: Optional[AggregateSource] = None,
    coarse: Optional[AggregateSource] = None,
    cement_psd_path: Optional[Path] = None,
    air_volume_fraction: float = 0.0,
    write_log: bool = True,
) -> ConcelasResult:
    """Run concelas post-processing for a completed elastic operation directory.

    Args:
        elastic_output_dir: Directory containing EffectiveModuli.csv and
            (optionally) ITZModuli.csv produced by thames -s 5.
        fine: Fine aggregate source (VF, K, G, grading). None to skip.
        coarse: Coarse aggregate source. None to skip.
        cement_psd_path: Path to the cement PSD file. If None or missing,
            the default median diameter (10 um) is used.
        air_volume_fraction: Entrained air as fraction of concrete (0-1).
        write_log: If True, write ConcelasLog.txt alongside the CSVs.

    Returns:
        The ConcelasResult; concrete rows are also appended to
        EffectiveModuli.csv as a side effect.

    Raises:
        MissingInputError: EffectiveModuli.csv is missing.
        ConcelasRunnerError: Files are malformed.
    """
    effective_csv = elastic_output_dir / "EffectiveModuli.csv"
    itz_csv = elastic_output_dir / "ITZModuli.csv"

    paste = read_effective_moduli(effective_csv)

    has_aggregate = (fine is not None) or (coarse is not None)
    itz_available = itz_csv.exists()

    if has_aggregate and itz_available:
        layers = read_itz_moduli(itz_csv)
        layer_k = layers.layer_k_gpa
        layer_g = layers.layer_g_gpa
        resolution_um = layers.resolution_um
        # agg_x is used by the service only as a "has aggregate" sentinel;
        # the actual slab position is encoded in the layer array length.
        agg_x = len(layer_k) + 1
    else:
        layer_k = []
        layer_g = []
        resolution_um = paste.resolution_um
        agg_x = 0
        if has_aggregate and not itz_available:
            logger.warning(
                "Aggregate sources supplied but ITZModuli.csv not found at %s; "
                "concelas will fall back to paste moduli as ITZ proxy",
                itz_csv,
            )

    cement_psd: List[Tuple[float, float]] = []
    if cement_psd_path is not None:
        cement_psd = read_cement_psd(cement_psd_path)

    result = run_concelas(
        paste_bulk_gpa=paste.bulk_gpa,
        paste_shear_gpa=paste.shear_gpa,
        layer_bulk_gpa=layer_k,
        layer_shear_gpa=layer_g,
        agg_x=agg_x,
        resolution_um=resolution_um,
        cement_psd=cement_psd,
        fine=fine,
        coarse=coarse,
        air_volume_fraction=air_volume_fraction,
    )

    append_concrete_rows(effective_csv, result)

    if write_log:
        write_concelas_log(elastic_output_dir / "ConcelasLog.txt", result)

    return result

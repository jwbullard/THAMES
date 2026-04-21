#!/usr/bin/env python3
"""
Concelas Service — concrete-scale elastic moduli and compressive strength.

Post-processes paste-scale FEM output from the THAMES C++ elastic solver
(EffectiveModuli.csv + ITZModuli.csv) together with aggregate grading and
elastic properties to produce concrete-scale effective moduli and
compressive strength estimates.

Algorithms ported from VCCTL backend/src/elastic.c (concelas, effective,
slope, mediansize functions, lines ~2942-3559). See those functions for
the mathematical background:

  - effective():  Hashin sphere-in-shell inclusion model with ITZ shell
  - slope():      Differential Mori-Tanaka volume-scaling rate
  - RK driver:    4th-order Runge-Kutta integration over shrinking matrix
                  volume fraction (1.0 -> target_matrix_vf)
  - mediansize(): Linear interpolation of cumulative PSD to find d50

This module contains only pure algorithms. File I/O and orchestration
live in concelas_runner.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Constants ported directly from elastic.c
_SHAPEFACTOR = 1.10       # concelas SHAPEFACTOR
_RKITS = 799              # number of RK sub-steps in matrix-volume integration
_H = -0.0010              # RK step size in matrix volume fraction
_DEFAULT_MEDIAN_DIAM_UM = 10.0
_AIR_DIAM_MM = 0.04       # virtual air-void size class
_AIR_POISSON = 0.4


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AggregateSource:
    """Grading and elastic properties for one aggregate source (fine or coarse)."""

    volume_fraction: float              # fraction of concrete (0-1)
    bulk_modulus_gpa: float              # K (GPa)
    shear_modulus_gpa: float              # G (GPa)
    grading: List[Tuple[float, float]]    # [(sieve_opening_mm, mass_fraction), ...]


@dataclass
class ConcelasResult:
    """Concrete-scale outputs from run_concelas()."""

    concrete_bulk_gpa: float
    concrete_shear_gpa: float
    concrete_young_gpa: float
    concrete_poisson: float
    itz_bulk_gpa: float
    itz_shear_gpa: float
    itz_width_um: float
    aggregate_volume_fraction: float
    air_volume_fraction: float
    matrix_volume_fraction: float
    mortar_cube_strength_mpa: float
    concrete_cube_strength_mpa: float
    cylinder_strength_mpa: float
    log_lines: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# mediansize — linear interp of cumulative PSD to find d50
# ---------------------------------------------------------------------------


def median_cement_psd(psd_points: List[Tuple[float, float]]) -> float:
    """Return the d50 (median diameter, micrometers) of a cement PSD.

    Args:
        psd_points: List of (diameter_um, volume_fraction) pairs, ordered
            by increasing diameter. ``volume_fraction`` is the incremental
            mass/volume fraction in that size bin (not cumulative).

    Returns:
        Median diameter in micrometers. Falls back to 10.0 um if the PSD
        is empty or unnormalized (does not reach 50% cumulative).

    Ports mediansize() from vcctl-gtk/backend/src/vcctllib/mediansize.c.
    """
    if not psd_points:
        return _DEFAULT_MEDIAN_DIAM_UM

    diam_lo = 0.0
    vol_lo = 0.0
    diam_hi = 0.0
    vol_hi = 0.0

    for diam, vol in psd_points:
        diam_lo = diam_hi
        vol_lo = vol_hi
        diam_hi = diam
        vol_hi += vol
        if vol_hi >= 0.5:
            if vol_hi == vol_lo:
                return diam_hi
            return diam_lo + (diam_hi - diam_lo) * (0.5 - vol_lo) / (vol_hi - vol_lo)

    # Unnormalized data -> default
    return _DEFAULT_MEDIAN_DIAM_UM


# ---------------------------------------------------------------------------
# ITZ / paste averaging from per-layer K[i], G[i] arrays
# ---------------------------------------------------------------------------


def compute_itz_and_paste_moduli(
    layer_k: List[float],
    layer_g: List[float],
    agg_x: int,
    itz_width_um: float,
    resolution_um: float,
    nx: Optional[int] = None,
    paste_k_fallback_gpa: float = 0.0,
    paste_g_fallback_gpa: float = 0.0,
) -> Tuple[float, float, float, float, int]:
    """Average per-voxel K[i], G[i] into ITZ and bulk-paste moduli.

    The layer arrays come from ITZModuli.csv where each row is already a
    symmetric average of the two voxel positions equidistant from the
    aggregate slab. So here we only need to mean over the first
    ``itz_pix`` voxels outward from the slab (ITZ) vs the remainder
    (bulk paste).

    Args:
        layer_k: Per-layer bulk moduli (GPa), indexed 0..nx-1.
        layer_g: Per-layer shear moduli (GPa), same indexing.
        agg_x: Aggregate slab surface position (voxel index).
        itz_width_um: ITZ thickness in micrometers (typically median cement
            diameter for Hill-Bentz formulation).
        resolution_um: Microstructure resolution, micrometers per voxel.
        nx: Grid X dimension. Required if layer arrays include both halves.
        paste_k_fallback_gpa: Returned for ``kitz``, ``kcem`` if no aggregate.
        paste_g_fallback_gpa: Returned for ``gitz``, ``gcem`` if no aggregate.

    Returns:
        Tuple of (kitz, gitz, kcem, gcem, itz_pix). All moduli in GPa,
        ``itz_pix`` is the ITZ width in voxels (int, >=1).

    Ports the block at elastic.c:3016-3072.
    """
    if agg_x <= 0 or not layer_k:
        return (paste_k_fallback_gpa, paste_g_fallback_gpa,
                paste_k_fallback_gpa, paste_g_fallback_gpa, 0)

    itz_pix = max(1, int(round(itz_width_um / resolution_um)))

    # ITZ layers: the itz_pix voxels immediately adjacent to the aggregate
    # slab. layer_k/layer_g are already symmetric averages, so we just mean
    # the first itz_pix entries (the rows closest to the slab surface).
    itz_pix_effective = min(itz_pix, len(layer_k))

    k_itz = sum(layer_k[:itz_pix_effective]) / itz_pix_effective
    g_itz = sum(layer_g[:itz_pix_effective]) / itz_pix_effective

    # Bulk paste: the remaining layers outside the ITZ
    remainder_k = layer_k[itz_pix_effective:]
    remainder_g = layer_g[itz_pix_effective:]
    if remainder_k:
        k_cem = sum(remainder_k) / len(remainder_k)
        g_cem = sum(remainder_g) / len(remainder_g)
    else:
        # ITZ filled the entire sampled region; reuse ITZ as paste estimate
        k_cem = k_itz
        g_cem = g_itz

    return (k_itz, g_itz, k_cem, g_cem, itz_pix)


# ---------------------------------------------------------------------------
# effective() — Hashin sphere-in-shell for each aggregate size class
# ---------------------------------------------------------------------------


def _effective(
    diam_mm: List[float],
    k_i: List[float],
    g_i: List[float],
    itz_width_mm: float,
    kitz: float,
    gitz: float,
    n_aggregate_classes: int,
) -> Tuple[List[float], List[float]]:
    """Apply ITZ correction to each aggregate size class.

    For each class i (0..n_aggregate_classes), replace the bare-aggregate
    K_i, G_i with effective composite-inclusion moduli that include the
    ITZ shell of thickness ``itz_width_mm`` around a sphere of diameter
    ``diam_mm[i]``. The air "class" at index n_aggregate_classes uses
    Poisson 0.4 for numerical stability.

    Returns:
        Tuple of (K_effective[], G_effective[]), one per size class.

    Ports effective() from elastic.c:3454-3537.
    """
    k_out: List[float] = [0.0] * (n_aggregate_classes + 1)
    g_out: List[float] = [0.0] * (n_aggregate_classes + 1)

    for i in range(n_aggregate_classes + 1):
        d = diam_mm[i]
        ba = d / (d + 2.0 * itz_width_mm) if (d + 2.0 * itz_width_mm) > 0 else 0.0
        c = ba ** 3.0

        # Poisson ratio of the inclusion and of the ITZ
        if i == n_aggregate_classes:
            nui = _AIR_POISSON
            nuitz = 0.0  # matches C code sentinel
        else:
            denom_i = 2.0 * ((3.0 * k_i[i]) + g_i[i])
            nui = ((3.0 * k_i[i]) - (2.0 * g_i[i])) / denom_i if denom_i != 0 else 0.25
            denom_itz = 2.0 * ((3.0 * kitz) + gitz)
            nuitz = ((3.0 * kitz) - (2.0 * gitz)) / denom_itz if denom_itz != 0 else 0.25

        # Effective bulk modulus (Hashin composite sphere)
        if i == n_aggregate_classes:
            # Air: K_i is 0, so denominator handling keeps result finite
            k_num = c * (0.0 - kitz)
            k_den = 1.0 + (1.0 - c) * (0.0 - kitz) / (kitz + (4.0 * gitz / 3.0)) \
                if (kitz + (4.0 * gitz / 3.0)) != 0 else 1.0
            k_out[i] = kitz + (k_num / k_den if k_den != 0 else 0.0)
        else:
            k_num = c * (k_i[i] - kitz)
            shell = kitz + (4.0 * gitz / 3.0)
            k_den = 1.0 + (1.0 - c) * (k_i[i] - kitz) / shell if shell != 0 else 1.0
            k_out[i] = kitz + (k_num / k_den if k_den != 0 else 0.0)

        # Effective shear modulus via Christensen's quadratic formula
        gi_val = g_i[i] if i < n_aggregate_classes else 0.0
        if gitz == 0.0:
            g_out[i] = 0.0
            continue
        geff = gi_val / gitz - 1.0

        eta1 = (geff * (7.0 - 10.0 * nuitz) * (7.0 + 5.0 * nui)
                + 105.0 * (nui - nuitz))
        eta2 = geff * (7.0 + 5.0 * nui) + 35.0 * (1.0 - nui)
        eta3 = geff * (8.0 - 10.0 * nuitz) + 15.0 * (1.0 - nuitz)

        c73 = c ** (7.0 / 3.0)
        c53 = c ** (5.0 / 3.0)
        c103 = c ** (10.0 / 3.0)

        aa = 8.0 * geff * (4.0 - 5.0 * nuitz) * eta1 * c103
        aa -= 2.0 * (63.0 * geff * eta2 + 2.0 * eta1 * eta3) * c73
        aa += 252.0 * geff * eta2 * c53
        aa -= 50.0 * geff * (7.0 - 12.0 * nuitz + 8.0 * nuitz * nuitz) * eta2 * c
        aa += 4.0 * (7.0 - 10.0 * nuitz) * eta2 * eta3

        bb = -2.0 * geff * (1.0 - 5.0 * nuitz) * eta1 * c103
        bb += 2.0 * (63.0 * geff * eta2 + 2.0 * eta1 * eta3) * c73
        bb -= 252.0 * geff * eta2 * c53
        bb += 75.0 * geff * (3.0 - nuitz) * eta2 * nuitz * c
        bb += 1.50 * (15.0 * nuitz - 7.0) * eta2 * eta3

        cc = 4.0 * geff * (5.0 * nuitz - 7.0) * eta1 * c103
        cc -= 2.0 * (63.0 * geff * eta2 + 2.0 * eta1 * eta3) * c73
        cc += 252.0 * geff * eta2 * c53
        cc += 25.0 * geff * (nuitz * nuitz - 7.0) * eta2 * c
        cc -= (7.0 + 5.0 * nuitz) * eta2 * eta3

        arg = 4.0 * bb * bb - 4.0 * aa * cc
        if aa != 0.0 and arg >= 0.0:
            gg_ratio = (-2.0 * bb + math.sqrt(arg)) / (2.0 * aa)
        else:
            gg_ratio = 0.0

        g_out[i] = gg_ratio * gitz

    return k_out, g_out


# ---------------------------------------------------------------------------
# slope() — differential Mori-Tanaka rate of change wrt matrix volume
# ---------------------------------------------------------------------------


def _slope(
    k_matrix: float,
    g_matrix: float,
    vf: List[float],
    k_i: List[float],
    g_i: List[float],
    n_classes: int,
) -> Tuple[float, float]:
    """Compute dK/dV_m and dG/dV_m for the RK integration.

    Ports slope() from elastic.c:3539-3558.
    """
    q = 4.0 / 3.0
    t = 8.0 / 9.0

    kk = 0.0
    gg = 0.0

    for i in range(n_classes + 1):
        if k_matrix == 0.0:
            continue
        k_term_num = (k_matrix + q * g_matrix) * (k_i[i] / k_matrix - 1.0)
        k_term_den = k_i[i] + q * g_matrix
        if k_term_den != 0.0:
            kk += vf[i] * (k_term_num / k_term_den)

        g_term_num = 5.0 * (k_matrix + q * g_matrix) * (g_i[i] - g_matrix)
        g_term_den = (3.0 * g_matrix * (k_matrix + t * g_matrix)
                      + 2.0 * g_i[i] * (k_matrix + 2.0 * g_matrix))
        if g_term_den != 0.0:
            gg += vf[i] * (g_term_num / g_term_den)

    kk *= _SHAPEFACTOR
    gg *= _SHAPEFACTOR

    return kk, gg


# ---------------------------------------------------------------------------
# Compressive strength fits (from elastic.c:3396-3420, SCG / Pichet fits)
# ---------------------------------------------------------------------------


def _compressive_strengths(young_modulus_gpa: float) -> Tuple[float, float, float]:
    """Return (mortar_cube, concrete_cube, cylinder) compressive strengths in MPa.

    Fits ported verbatim from elastic.c:3396-3420. The cylinder strength is
    reported as 0.624 * concrete_cube (industry convention) rather than the
    separate Pichet cylinder fit, matching the C code's fpout line.
    """
    if young_modulus_gpa <= 0.0:
        return (0.0, 0.0, 0.0)
    mortar_cube = 5.0e-4 * (young_modulus_gpa ** 3.18577)
    concrete_cube = 5.0e-4 * (young_modulus_gpa ** 3.0586)
    cylinder = 0.624 * concrete_cube
    return (mortar_cube, concrete_cube, cylinder)


# ---------------------------------------------------------------------------
# run_concelas — top-level orchestrator
# ---------------------------------------------------------------------------


def _prepare_aggregate_classes(
    fine: Optional[AggregateSource],
    coarse: Optional[AggregateSource],
    air_volume_fraction: float,
) -> Tuple[List[float], List[float], List[float], List[float], List[float], float, float]:
    """Build merged, sorted, normalized size-class arrays from fine + coarse sources.

    Returns:
        (diam_mm[], vf[], ki[], gi[], ki_preserved[], fine_vf_total, coarse_vf_total)
        where ki_preserved is a copy of the unmodified inclusion K values (Ki_concelas
        in the C code) used by effective() and slope() separately. The arrays
        include a trailing air class at index n_classes.

    Ports elastic.c:3100-3340 (reading, sorting, averaging, normalizing).
    """
    diam: List[float] = []
    vf: List[float] = []
    k_vals: List[float] = []
    g_vals: List[float] = []

    fine_vf_total = 0.0
    coarse_vf_total = 0.0

    fine_begin = 0
    fine_end = 0
    if fine is not None and fine.volume_fraction > 0.0 and fine.grading:
        fine_begin = len(diam)
        for sieve_mm, mass_frac in fine.grading:
            diam.append(sieve_mm)
            vf.append(fine.volume_fraction * mass_frac)
            k_vals.append(fine.bulk_modulus_gpa)
            g_vals.append(fine.shear_modulus_gpa)
        fine_end = len(diam)
        fine_vf_total = fine.volume_fraction

    coarse_begin = len(diam)
    coarse_end = len(diam)
    if coarse is not None and coarse.volume_fraction > 0.0 and coarse.grading:
        coarse_begin = len(diam)
        for sieve_mm, mass_frac in coarse.grading:
            diam.append(sieve_mm)
            vf.append(coarse.volume_fraction * mass_frac)
            k_vals.append(coarse.bulk_modulus_gpa)
            g_vals.append(coarse.shear_modulus_gpa)
        coarse_end = len(diam)
        coarse_vf_total = coarse.volume_fraction

    n = len(diam)

    # Sort descending within each aggregate source (bubble sort matches C code)
    def _sort_desc(start: int, stop: int) -> None:
        for i in range(start, stop - 1):
            for j in range(i + 1, stop):
                if diam[i] < diam[j]:
                    diam[i], diam[j] = diam[j], diam[i]
                    vf[i], vf[j] = vf[j], vf[i]
                    k_vals[i], k_vals[j] = k_vals[j], k_vals[i]
                    g_vals[i], g_vals[j] = g_vals[j], g_vals[i]

    _sort_desc(fine_begin, fine_end)
    _sort_desc(coarse_begin, coarse_end)

    # Average each diameter with its predecessor inside the same source,
    # scale the largest up by 1.10 (C code lines 3268-3276)
    if fine_end - fine_begin > 1:
        for i in range(fine_begin + 1, fine_end):
            diam[i] = 0.5 * (diam[i] + diam[i - 1])
    if fine_end > fine_begin:
        diam[fine_begin] *= 1.10

    if coarse_end - coarse_begin > 1:
        for i in range(coarse_begin + 1, coarse_end):
            diam[i] = 0.5 * (diam[i] + diam[i - 1])
    if coarse_end > coarse_begin:
        diam[coarse_begin] *= 1.10

    # Final descending sort of the combined grading (C code lines 3278-3303)
    _sort_desc(0, n)

    # Renormalize volume fractions if they don't sum to 1.0 within tolerance
    vf_sum = sum(vf)
    if n > 0 and abs(vf_sum - 1.0) > 0.005 and vf_sum > 0.0:
        vf = [v / vf_sum for v in vf]

    agg_frac = fine_vf_total + coarse_vf_total
    air_frac = max(0.0, air_volume_fraction)

    # Rescale aggregate fractions to share with air (C code lines 3331-3333)
    if agg_frac + air_frac > 0.0:
        scale = agg_frac / (agg_frac + air_frac)
        vf = [v * scale for v in vf]

    # Append air "class" at end (C code lines 3334-3339)
    diam.append(_AIR_DIAM_MM)
    k_vals.append(0.0)
    g_vals.append(0.0)
    if agg_frac + air_frac > 0.0:
        vf.append(air_frac / (agg_frac + air_frac))
    else:
        vf.append(0.0)

    # Preserved copy of inclusion K, G (C code uses Ki_concelas/Gi_concelas
    # to remember the bare aggregate values separately from the ITZ-adjusted
    # K_concelas/G_concelas used by slope())
    k_preserved = list(k_vals)
    g_preserved = list(g_vals)

    return diam, vf, k_vals, g_vals, k_preserved, fine_vf_total, coarse_vf_total


def run_concelas(
    paste_bulk_gpa: float,
    paste_shear_gpa: float,
    layer_bulk_gpa: List[float],
    layer_shear_gpa: List[float],
    agg_x: int,
    resolution_um: float,
    cement_psd: List[Tuple[float, float]],
    fine: Optional[AggregateSource],
    coarse: Optional[AggregateSource],
    air_volume_fraction: float = 0.0,
) -> ConcelasResult:
    """Compute concrete-scale effective moduli and strengths.

    Top-level entry point ported from concelas() in elastic.c:2954-3452.

    Args:
        paste_bulk_gpa: Effective paste bulk modulus (GPa).
        paste_shear_gpa: Effective paste shear modulus (GPa).
        layer_bulk_gpa: Per-layer paste K profile from ITZModuli.csv (GPa),
            indexed from the aggregate surface outward.
        layer_shear_gpa: Per-layer paste G profile (GPa), same indexing.
        agg_x: Aggregate slab surface position (voxel index).
        resolution_um: Microstructure resolution in um/voxel.
        cement_psd: List of (diameter_um, mass_fraction) for the cement.
        fine: Fine aggregate source (or None).
        coarse: Coarse aggregate source (or None).
        air_volume_fraction: Entrained air (0-1, fraction of concrete).

    Returns:
        ConcelasResult with moduli and strengths.
    """
    log: List[str] = []

    # Step 1: cement median diameter -> ITZ width (micrometers -> mm)
    itz_width_um = median_cement_psd(cement_psd) if cement_psd else _DEFAULT_MEDIAN_DIAM_UM
    log.append(f"Median cement diameter = {itz_width_um:.3f} um -> ITZ width")

    # Step 2: split layer profile into ITZ and bulk paste averages
    kitz, gitz, kcem, gcem, itz_pix = compute_itz_and_paste_moduli(
        layer_k=layer_bulk_gpa,
        layer_g=layer_shear_gpa,
        agg_x=agg_x,
        itz_width_um=itz_width_um,
        resolution_um=resolution_um,
        paste_k_fallback_gpa=paste_bulk_gpa,
        paste_g_fallback_gpa=paste_shear_gpa,
    )
    log.append(f"ITZ pixel width = {itz_pix}, kitz = {kitz:.4f} GPa, gitz = {gitz:.4f} GPa")
    log.append(f"Bulk paste kcem = {kcem:.4f} GPa, gcem = {gcem:.4f} GPa")

    # Convert ITZ width to mm for use inside effective()
    itz_width_mm = itz_width_um * 0.001

    # Step 3: merge + normalize aggregate grading
    diam_mm, vf_list, k_vals, g_vals, k_preserved, fine_vf, coarse_vf = \
        _prepare_aggregate_classes(fine, coarse, air_volume_fraction)

    n_classes = len(diam_mm) - 1  # last entry is air
    agg_frac = fine_vf + coarse_vf
    air_frac = air_volume_fraction
    target_matrix_vf = 1.0 - (agg_frac + air_frac)

    log.append(f"Aggregate volume fraction = {agg_frac:.4f}")
    log.append(f"Air volume fraction = {air_frac:.4f}")
    log.append(f"Target matrix (paste) volume fraction = {target_matrix_vf:.4f}")

    if n_classes == 0 or target_matrix_vf >= 1.0 - 1e-9:
        # Degenerate case: paste only
        e_paste = _young_from_kg(paste_bulk_gpa, paste_shear_gpa)
        mortar, ccube, cyl = _compressive_strengths(e_paste)
        return ConcelasResult(
            concrete_bulk_gpa=paste_bulk_gpa,
            concrete_shear_gpa=paste_shear_gpa,
            concrete_young_gpa=e_paste,
            concrete_poisson=_poisson_from_kg(paste_bulk_gpa, paste_shear_gpa),
            itz_bulk_gpa=paste_bulk_gpa,
            itz_shear_gpa=paste_shear_gpa,
            itz_width_um=itz_width_um,
            aggregate_volume_fraction=0.0,
            air_volume_fraction=air_frac,
            matrix_volume_fraction=1.0,
            mortar_cube_strength_mpa=mortar,
            concrete_cube_strength_mpa=ccube,
            cylinder_strength_mpa=cyl,
            log_lines=log,
        )

    # Step 4: apply effective() ITZ correction to each size class
    # k_preserved / g_vals are the bare inclusion moduli (Ki_concelas / Gi_concelas).
    # _effective returns adjusted K / G values used by _slope (K_concelas / G_concelas).
    k_effective, g_effective = _effective(
        diam_mm=diam_mm,
        k_i=k_preserved,
        g_i=g_vals,
        itz_width_mm=itz_width_mm,
        kitz=kitz,
        gitz=gitz,
        n_aggregate_classes=n_classes,
    )

    # Step 5: 4th-order RK integration of the differential Mori-Tanaka problem
    k_m = kcem
    g_m = gcem
    ksave = [k_m]
    gsave = [g_m]
    xx = [1.0]

    for i in range(_RKITS):
        x_next = 1.0 + (i + 1) * _H
        xx.append(x_next)

        kk1, gg1 = _slope(k_m, g_m, vf_list, k_effective, g_effective, n_classes)
        q1 = -_H * g_m * gg1 / xx[i] if xx[i] != 0 else 0.0
        r1 = -_H * k_m * kk1 / xx[i] if xx[i] != 0 else 0.0

        kk2, gg2 = _slope(k_m + r1 / 2.0, g_m + q1 / 2.0, vf_list,
                          k_effective, g_effective, n_classes)
        x_half = xx[i] + 0.5 * _H
        q2 = -_H * (g_m + q1 / 2.0) * gg2 / x_half if x_half != 0 else 0.0
        r2 = -_H * (k_m + r1 / 2.0) * kk2 / x_half if x_half != 0 else 0.0

        kk3, gg3 = _slope(k_m + r2 / 2.0, g_m + q2 / 2.0, vf_list,
                          k_effective, g_effective, n_classes)
        q3 = -_H * (g_m + q2 / 2.0) * gg3 / x_half if x_half != 0 else 0.0
        r3 = -_H * (k_m + r2 / 2.0) * kk3 / x_half if x_half != 0 else 0.0

        kk4, gg4 = _slope(k_m + r3, g_m + q3, vf_list,
                          k_effective, g_effective, n_classes)
        x_full = xx[i] + _H
        q4 = -_H * (g_m + q3) * gg4 / x_full if x_full != 0 else 0.0
        r4 = -_H * (k_m + r3) * kk4 / x_full if x_full != 0 else 0.0

        q5 = (q1 + 2.0 * q2 + 2.0 * q3 + q4) / 6.0
        r5 = (r1 + 2.0 * r2 + 2.0 * r3 + r4) / 6.0

        g_m += q5
        k_m += r5

        gsave.append(g_m)
        ksave.append(k_m)

        if x_next < target_matrix_vf:
            # Linear interpolation onto target matrix volume (C code lines 3392-3398)
            z = (target_matrix_vf - xx[i]) / (xx[i + 1] - xx[i])
            g_final = gsave[i] + z * (gsave[i + 1] - gsave[i])
            k_final = ksave[i] + z * (ksave[i + 1] - ksave[i])
            k_m = k_final
            g_m = g_final
            break

    e_concrete = _young_from_kg(k_m, g_m)
    nu_concrete = _poisson_from_kg(k_m, g_m)
    mortar, ccube, cyl = _compressive_strengths(e_concrete)

    log.append(f"Concrete bulk  K = {k_m:.4f} GPa")
    log.append(f"Concrete shear G = {g_m:.4f} GPa")
    log.append(f"Concrete Young E = {e_concrete:.4f} GPa")
    log.append(f"Mortar cube strength   = {mortar:.4f} MPa")
    log.append(f"Concrete cube strength = {ccube:.4f} MPa")
    log.append(f"Cylinder strength      = {cyl:.4f} MPa")

    return ConcelasResult(
        concrete_bulk_gpa=k_m,
        concrete_shear_gpa=g_m,
        concrete_young_gpa=e_concrete,
        concrete_poisson=nu_concrete,
        itz_bulk_gpa=kitz,
        itz_shear_gpa=gitz,
        itz_width_um=itz_width_um,
        aggregate_volume_fraction=agg_frac,
        air_volume_fraction=air_frac,
        matrix_volume_fraction=target_matrix_vf,
        mortar_cube_strength_mpa=mortar,
        concrete_cube_strength_mpa=ccube,
        cylinder_strength_mpa=cyl,
        log_lines=log,
    )


# ---------------------------------------------------------------------------
# Elastic helpers
# ---------------------------------------------------------------------------


def _young_from_kg(k: float, g: float) -> float:
    denom = 3.0 * k + g
    if denom <= 0.0:
        return 0.0
    return 9.0 * k * g / denom


def _poisson_from_kg(k: float, g: float) -> float:
    denom = 2.0 * (3.0 * k + g)
    if denom == 0.0:
        return 0.0
    return (3.0 * k - 2.0 * g) / denom

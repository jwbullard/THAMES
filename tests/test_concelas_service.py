#!/usr/bin/env python3
"""
Tests for the Concelas Service (concrete-scale elastic moduli).

Run with: python -m pytest tests/test_concelas_service.py -v
Or simply: python tests/test_concelas_service.py
"""

import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.concelas_service import (
    AggregateSource,
    ConcelasResult,
    median_cement_psd,
    run_concelas,
    _young_from_kg,
    _poisson_from_kg,
    _compressive_strengths,
    compute_itz_and_paste_moduli,
)


class TestMedianCementPSD(unittest.TestCase):
    """Linear-interpolation median of cumulative PSD."""

    def test_empty_psd_returns_default(self) -> None:
        self.assertEqual(median_cement_psd([]), 10.0)

    def test_unnormalized_returns_default(self) -> None:
        # Cumulative stops at 0.3; should fall back to default
        self.assertEqual(median_cement_psd([(1.0, 0.1), (5.0, 0.2)]), 10.0)

    def test_exact_midpoint(self) -> None:
        # First bin takes us to 0.5 exactly at diameter 10
        result = median_cement_psd([(10.0, 0.5), (20.0, 0.5)])
        self.assertAlmostEqual(result, 10.0, places=4)

    def test_interpolates_between_bins(self) -> None:
        # Cumulative crosses 0.5 in the second bin
        # After bin 1: d_lo=1, vol_lo=0.25
        # After bin 2: d_hi=5, vol_hi=0.75 -> interpolate
        # result = 1 + (5-1)*(0.5-0.25)/(0.75-0.25) = 1 + 4*0.5 = 3
        result = median_cement_psd([(1.0, 0.25), (5.0, 0.5), (10.0, 0.25)])
        self.assertAlmostEqual(result, 3.0, places=4)

    def test_realistic_cement_psd(self) -> None:
        # Simulated Type I cement PSD, log-normal-ish
        psd = [
            (1.0, 0.05),
            (3.0, 0.15),
            (10.0, 0.30),   # cumulative 0.50 here
            (30.0, 0.30),
            (100.0, 0.20),
        ]
        result = median_cement_psd(psd)
        # Interpolation lands at diameter 10 exactly
        self.assertAlmostEqual(result, 10.0, places=4)


class TestYoungPoisson(unittest.TestCase):
    """Young's modulus and Poisson's ratio from K, G."""

    def test_zero_moduli(self) -> None:
        self.assertEqual(_young_from_kg(0.0, 0.0), 0.0)
        self.assertEqual(_poisson_from_kg(0.0, 0.0), 0.0)

    def test_typical_paste(self) -> None:
        # K=15 GPa, G=10 GPa -> E = 9*15*10/(3*15+10) = 1350/55 = 24.545
        e = _young_from_kg(15.0, 10.0)
        self.assertAlmostEqual(e, 24.5454545, places=5)
        # nu = (3*15 - 2*10) / (2*(3*15+10)) = 25/110 = 0.22727
        nu = _poisson_from_kg(15.0, 10.0)
        self.assertAlmostEqual(nu, 0.22727, places=4)


class TestCompressiveStrengths(unittest.TestCase):
    """Power-law strength fits from elastic.c."""

    def test_zero_young_returns_zeros(self) -> None:
        mortar, ccube, cyl = _compressive_strengths(0.0)
        self.assertEqual((mortar, ccube, cyl), (0.0, 0.0, 0.0))

    def test_monotone_increase(self) -> None:
        # Strengths should grow with Young's modulus
        m1, c1, cyl1 = _compressive_strengths(20.0)
        m2, c2, cyl2 = _compressive_strengths(40.0)
        self.assertGreater(m2, m1)
        self.assertGreater(c2, c1)
        self.assertGreater(cyl2, cyl1)

    def test_cylinder_is_0p624_of_cube(self) -> None:
        mortar, ccube, cyl = _compressive_strengths(30.0)
        self.assertAlmostEqual(cyl, 0.624 * ccube, places=6)

    def test_ported_formula_values(self) -> None:
        # Spot-check the ported power-law fits at E = 30 GPa
        # mortar_cube = 5e-4 * 30^3.18577 ≈ 20.3 MPa
        mortar, ccube, cyl = _compressive_strengths(30.0)
        self.assertAlmostEqual(mortar, 5.0e-4 * (30.0 ** 3.18577), places=6)
        self.assertAlmostEqual(ccube, 5.0e-4 * (30.0 ** 3.0586), places=6)


class TestComputeItzAndPasteModuli(unittest.TestCase):
    """ITZ vs bulk-paste averaging from per-layer arrays."""

    def test_no_aggregate_returns_fallbacks(self) -> None:
        kitz, gitz, kcem, gcem, itz_pix = compute_itz_and_paste_moduli(
            layer_k=[10.0, 12.0],
            layer_g=[6.0, 7.0],
            agg_x=0,                    # aggregate absent
            itz_width_um=10.0,
            resolution_um=1.0,
            paste_k_fallback_gpa=15.0,
            paste_g_fallback_gpa=9.0,
        )
        self.assertEqual((kitz, gitz, kcem, gcem, itz_pix), (15.0, 9.0, 15.0, 9.0, 0))

    def test_itz_layers_are_first_n_voxels(self) -> None:
        # 10 layer entries; ITZ width 3 um / 1 um/voxel -> 3 voxels
        layer_k = [8.0, 8.2, 8.4, 11.0, 11.2, 11.4, 11.6, 11.8, 12.0, 12.2]
        layer_g = [4.0, 4.1, 4.2, 6.0, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6]
        kitz, gitz, kcem, gcem, itz_pix = compute_itz_and_paste_moduli(
            layer_k=layer_k,
            layer_g=layer_g,
            agg_x=50,
            itz_width_um=3.0,
            resolution_um=1.0,
        )
        self.assertEqual(itz_pix, 3)
        self.assertAlmostEqual(kitz, (8.0 + 8.2 + 8.4) / 3, places=6)
        self.assertAlmostEqual(gitz, (4.0 + 4.1 + 4.2) / 3, places=6)
        self.assertAlmostEqual(kcem, sum(layer_k[3:]) / 7, places=6)
        self.assertAlmostEqual(gcem, sum(layer_g[3:]) / 7, places=6)

    def test_itz_pix_minimum_is_one(self) -> None:
        # Very small ITZ width rounds to 0, but we enforce minimum 1
        _, _, _, _, itz_pix = compute_itz_and_paste_moduli(
            layer_k=[10.0, 11.0, 12.0],
            layer_g=[6.0, 6.5, 7.0],
            agg_x=1,
            itz_width_um=0.1,
            resolution_um=1.0,
        )
        self.assertEqual(itz_pix, 1)


class TestRunConcelasDegenerate(unittest.TestCase):
    """Degenerate cases: no aggregate -> concrete moduli equal paste moduli."""

    def test_no_aggregate_no_air(self) -> None:
        result = run_concelas(
            paste_bulk_gpa=15.0,
            paste_shear_gpa=10.0,
            layer_bulk_gpa=[],
            layer_shear_gpa=[],
            agg_x=0,
            resolution_um=1.0,
            cement_psd=[(1.0, 0.5), (10.0, 0.5)],
            fine=None,
            coarse=None,
            air_volume_fraction=0.0,
        )
        self.assertAlmostEqual(result.concrete_bulk_gpa, 15.0, places=6)
        self.assertAlmostEqual(result.concrete_shear_gpa, 10.0, places=6)
        self.assertAlmostEqual(result.aggregate_volume_fraction, 0.0, places=6)
        self.assertEqual(result.matrix_volume_fraction, 1.0)

    def test_no_aggregate_returns_valid_result(self) -> None:
        result = run_concelas(
            paste_bulk_gpa=12.0,
            paste_shear_gpa=8.0,
            layer_bulk_gpa=[],
            layer_shear_gpa=[],
            agg_x=0,
            resolution_um=1.0,
            cement_psd=[],
            fine=None,
            coarse=None,
            air_volume_fraction=0.02,
        )
        # Paste-only: concrete moduli == paste moduli
        self.assertGreater(result.concrete_young_gpa, 0.0)
        self.assertGreater(result.mortar_cube_strength_mpa, 0.0)


class TestRunConcelasRealistic(unittest.TestCase):
    """Realistic case: paste + aggregate -> reasonable stiffening."""

    def _build_layer_profile(self, nx: int, kbulk: float, gshear: float) -> tuple:
        """Return uniform per-voxel K, G profiles (no ITZ gradient)."""
        return ([kbulk] * nx, [gshear] * nx)

    def test_stiffer_aggregate_raises_concrete_modulus(self) -> None:
        """Adding a stiff aggregate should stiffen the composite."""
        # Paste moduli: K=12 GPa, G=8 GPa (typical hydrated paste)
        paste_k, paste_g = 12.0, 8.0
        layer_k, layer_g = self._build_layer_profile(50, paste_k, paste_g)

        fine = AggregateSource(
            volume_fraction=0.35,
            bulk_modulus_gpa=37.0,     # quartz sand K
            shear_modulus_gpa=44.0,     # quartz sand G
            grading=[(4.75, 0.1), (2.36, 0.2), (1.18, 0.3), (0.6, 0.25), (0.3, 0.15)],
        )
        coarse = AggregateSource(
            volume_fraction=0.35,
            bulk_modulus_gpa=45.0,     # limestone K
            shear_modulus_gpa=30.0,     # limestone G
            grading=[(25.0, 0.2), (19.0, 0.3), (12.5, 0.3), (9.5, 0.2)],
        )
        cement_psd = [(1.0, 0.1), (5.0, 0.3), (15.0, 0.4), (50.0, 0.2)]

        result = run_concelas(
            paste_bulk_gpa=paste_k,
            paste_shear_gpa=paste_g,
            layer_bulk_gpa=layer_k,
            layer_shear_gpa=layer_g,
            agg_x=25,
            resolution_um=1.0,
            cement_psd=cement_psd,
            fine=fine,
            coarse=coarse,
            air_volume_fraction=0.02,
        )

        # Concrete should be stiffer than paste (fine + coarse combined VF = 0.70)
        self.assertGreater(result.concrete_bulk_gpa, paste_k * 1.2,
            f"Concrete K {result.concrete_bulk_gpa:.2f} should exceed paste K {paste_k}")
        self.assertGreater(result.concrete_shear_gpa, paste_g * 1.1,
            f"Concrete G {result.concrete_shear_gpa:.2f} should exceed paste G {paste_g}")

        # Strengths should be positive
        self.assertGreater(result.mortar_cube_strength_mpa, 0.0)
        self.assertGreater(result.concrete_cube_strength_mpa, 0.0)
        self.assertGreater(result.cylinder_strength_mpa, 0.0)

        # Volume fractions consistent
        self.assertAlmostEqual(
            result.aggregate_volume_fraction + result.air_volume_fraction
            + result.matrix_volume_fraction,
            1.0, places=5
        )

    def test_only_fine_aggregate(self) -> None:
        """Fine aggregate alone should also stiffen."""
        paste_k, paste_g = 12.0, 8.0
        layer_k, layer_g = self._build_layer_profile(50, paste_k, paste_g)

        fine = AggregateSource(
            volume_fraction=0.45,
            bulk_modulus_gpa=37.0,
            shear_modulus_gpa=44.0,
            grading=[(2.0, 0.3), (1.0, 0.4), (0.5, 0.3)],
        )

        result = run_concelas(
            paste_bulk_gpa=paste_k,
            paste_shear_gpa=paste_g,
            layer_bulk_gpa=layer_k,
            layer_shear_gpa=layer_g,
            agg_x=25,
            resolution_um=1.0,
            cement_psd=[(10.0, 0.5), (20.0, 0.5)],
            fine=fine,
            coarse=None,
            air_volume_fraction=0.0,
        )

        self.assertGreater(result.concrete_bulk_gpa, paste_k)
        self.assertAlmostEqual(result.aggregate_volume_fraction, 0.45, places=5)

    def test_only_coarse_aggregate(self) -> None:
        """Coarse aggregate alone should stiffen."""
        paste_k, paste_g = 12.0, 8.0
        layer_k, layer_g = self._build_layer_profile(50, paste_k, paste_g)

        coarse = AggregateSource(
            volume_fraction=0.40,
            bulk_modulus_gpa=50.0,
            shear_modulus_gpa=35.0,
            grading=[(25.0, 0.4), (12.5, 0.4), (9.5, 0.2)],
        )

        result = run_concelas(
            paste_bulk_gpa=paste_k,
            paste_shear_gpa=paste_g,
            layer_bulk_gpa=layer_k,
            layer_shear_gpa=layer_g,
            agg_x=25,
            resolution_um=1.0,
            cement_psd=[(10.0, 1.0)],
            fine=None,
            coarse=coarse,
            air_volume_fraction=0.0,
        )

        self.assertGreater(result.concrete_bulk_gpa, paste_k)
        self.assertAlmostEqual(result.aggregate_volume_fraction, 0.40, places=5)

    def test_higher_air_reduces_modulus(self) -> None:
        """Entrained air should soften the composite at fixed aggregate."""
        paste_k, paste_g = 12.0, 8.0
        layer_k, layer_g = self._build_layer_profile(50, paste_k, paste_g)
        fine = AggregateSource(
            volume_fraction=0.45,
            bulk_modulus_gpa=37.0,
            shear_modulus_gpa=44.0,
            grading=[(2.0, 0.5), (1.0, 0.5)],
        )

        low_air = run_concelas(
            paste_bulk_gpa=paste_k, paste_shear_gpa=paste_g,
            layer_bulk_gpa=layer_k, layer_shear_gpa=layer_g,
            agg_x=25, resolution_um=1.0,
            cement_psd=[(10.0, 1.0)],
            fine=fine, coarse=None,
            air_volume_fraction=0.01,
        )
        high_air = run_concelas(
            paste_bulk_gpa=paste_k, paste_shear_gpa=paste_g,
            layer_bulk_gpa=layer_k, layer_shear_gpa=layer_g,
            agg_x=25, resolution_um=1.0,
            cement_psd=[(10.0, 1.0)],
            fine=fine, coarse=None,
            air_volume_fraction=0.08,
        )

        self.assertGreater(low_air.concrete_bulk_gpa, high_air.concrete_bulk_gpa)
        self.assertGreater(low_air.concrete_shear_gpa, high_air.concrete_shear_gpa)


class TestConcelasResultStructure(unittest.TestCase):
    """Return type and key completeness."""

    def test_result_has_all_fields(self) -> None:
        result = run_concelas(
            paste_bulk_gpa=12.0, paste_shear_gpa=8.0,
            layer_bulk_gpa=[], layer_shear_gpa=[],
            agg_x=0, resolution_um=1.0,
            cement_psd=[],
            fine=None, coarse=None,
            air_volume_fraction=0.0,
        )
        self.assertIsInstance(result, ConcelasResult)
        # All numeric fields are floats
        for field_name in (
            'concrete_bulk_gpa', 'concrete_shear_gpa', 'concrete_young_gpa',
            'concrete_poisson', 'itz_bulk_gpa', 'itz_shear_gpa', 'itz_width_um',
            'aggregate_volume_fraction', 'air_volume_fraction',
            'matrix_volume_fraction', 'mortar_cube_strength_mpa',
            'concrete_cube_strength_mpa', 'cylinder_strength_mpa',
        ):
            self.assertIsInstance(getattr(result, field_name), float, field_name)
        self.assertIsInstance(result.log_lines, list)


if __name__ == "__main__":
    unittest.main()

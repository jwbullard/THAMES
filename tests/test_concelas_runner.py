#!/usr/bin/env python3
"""
Tests for the Concelas Runner (CSV I/O + orchestration).

Run with: python -m pytest tests/test_concelas_runner.py -v
Or simply: python tests/test_concelas_runner.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.concelas_service import AggregateSource
from app.services.concelas_runner import (
    ConcelasRunnerError,
    MissingInputError,
    append_concrete_rows,
    read_cement_psd,
    read_effective_moduli,
    read_grading_file,
    read_itz_moduli,
    run_and_append,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SAMPLE_EFFECTIVE = """Property,Value,Units
Microstructure,hytest,
X_Dimension,100,voxels
Y_Dimension,100,voxels
Z_Dimension,100,voxels
Resolution, 1.0,um/voxel
Bulk_modulus,12.3,GPa
Shear_modulus,8.1,GPa
Youngs_modulus,20.2,GPa
Poissons_ratio,0.247,
"""

_SAMPLE_ITZ = """Property,Value,Units
Microstructure,hytest,
X_Dimension,100,voxels
Y_Dimension,100,voxels
Z_Dimension,100,voxels
Resolution,1.0,um/voxel
Layer_1_distance,0.5,um
Layer_1_Bulk_modulus,6.5,GPa
Layer_1_Shear_modulus,4.0,GPa
Layer_1_Youngs_modulus,10.1,GPa
Layer_1_Poissons_ratio,0.22,
Layer_0_distance,1.5,um
Layer_0_Bulk_modulus,7.0,GPa
Layer_0_Shear_modulus,4.3,GPa
Layer_0_Youngs_modulus,10.8,GPa
Layer_0_Poissons_ratio,0.22,
Layer_-1_distance,2.5,um
Layer_-1_Bulk_modulus,10.0,GPa
Layer_-1_Shear_modulus,6.5,GPa
Layer_-1_Youngs_modulus,16.2,GPa
Layer_-1_Poissons_ratio,0.24,
Layer_-2_distance,3.5,um
Layer_-2_Bulk_modulus,12.0,GPa
Layer_-2_Shear_modulus,8.0,GPa
Layer_-2_Youngs_modulus,19.7,GPa
Layer_-2_Poissons_ratio,0.23,
"""


_SAMPLE_PSD = """diameter_um,volume_fraction
1.0,0.10
5.0,0.30
15.0,0.40
50.0,0.20
"""


_SAMPLE_GRADING = """opening_mm,mass_fraction
4.75,0.10
2.36,0.30
1.18,0.35
0.60,0.15
0.30,0.10
"""


# ---------------------------------------------------------------------------
# Tests: CSV parsers
# ---------------------------------------------------------------------------


class TestReadEffectiveModuli(unittest.TestCase):
    def test_parses_paste_moduli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "EffectiveModuli.csv"
            p.write_text(_SAMPLE_EFFECTIVE)
            paste = read_effective_moduli(p)
        self.assertAlmostEqual(paste.bulk_gpa, 12.3)
        self.assertAlmostEqual(paste.shear_gpa, 8.1)
        self.assertAlmostEqual(paste.young_gpa, 20.2)
        self.assertAlmostEqual(paste.poisson, 0.247)
        self.assertAlmostEqual(paste.resolution_um, 1.0)
        self.assertEqual(paste.nx, 100)
        self.assertEqual(paste.microstructure_name, "hytest")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(MissingInputError):
            read_effective_moduli(Path("/no/such/file.csv"))

    def test_malformed_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "EffectiveModuli.csv"
            p.write_text("Property,Value,Units\nBogus,notanumber,GPa\n")
            with self.assertRaises(ConcelasRunnerError):
                read_effective_moduli(p)


class TestReadItzModuli(unittest.TestCase):
    def test_parses_and_sorts_layers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ITZModuli.csv"
            p.write_text(_SAMPLE_ITZ)
            layers = read_itz_moduli(p)
        self.assertEqual(len(layers.layer_k_gpa), 4)
        # Layers ordered by distance (nearest to slab first)
        self.assertEqual(layers.layer_distance_um, [0.5, 1.5, 2.5, 3.5])
        self.assertEqual(layers.layer_k_gpa, [6.5, 7.0, 10.0, 12.0])
        self.assertEqual(layers.layer_g_gpa, [4.0, 4.3, 6.5, 8.0])
        self.assertEqual(layers.nx, 100)
        self.assertAlmostEqual(layers.resolution_um, 1.0)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(MissingInputError):
            read_itz_moduli(Path("/no/such/file.csv"))


class TestReadCementPsd(unittest.TestCase):
    def test_parses_psd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cement_psd.csv"
            p.write_text(_SAMPLE_PSD)
            psd = read_cement_psd(p)
        self.assertEqual(len(psd), 4)
        self.assertEqual(psd[0], (1.0, 0.10))
        self.assertEqual(psd[-1], (50.0, 0.20))

    def test_missing_file_returns_empty(self) -> None:
        psd = read_cement_psd(Path("/no/such/cement_psd.csv"))
        self.assertEqual(psd, [])

    def test_numeric_header_not_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "psd.csv"
            p.write_text("1.0,0.5\n5.0,0.5\n")
            psd = read_cement_psd(p)
        self.assertEqual(len(psd), 2)


class TestReadGradingFile(unittest.TestCase):
    def test_parses_grading(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "grading.csv"
            p.write_text(_SAMPLE_GRADING)
            grading = read_grading_file(p)
        self.assertEqual(len(grading), 5)
        self.assertEqual(grading[0], (4.75, 0.10))


# ---------------------------------------------------------------------------
# Tests: appending concrete rows
# ---------------------------------------------------------------------------


class TestAppendConcreteRows(unittest.TestCase):
    def _build_result(self):
        from app.services.concelas_service import ConcelasResult
        return ConcelasResult(
            concrete_bulk_gpa=25.3,
            concrete_shear_gpa=15.8,
            concrete_young_gpa=39.2,
            concrete_poisson=0.240,
            itz_bulk_gpa=6.8,
            itz_shear_gpa=4.1,
            itz_width_um=10.0,
            aggregate_volume_fraction=0.70,
            air_volume_fraction=0.02,
            matrix_volume_fraction=0.28,
            mortar_cube_strength_mpa=45.6,
            concrete_cube_strength_mpa=38.9,
            cylinder_strength_mpa=24.3,
            log_lines=["one", "two"],
        )

    def test_rows_appear_in_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "EffectiveModuli.csv"
            p.write_text(_SAMPLE_EFFECTIVE)
            append_concrete_rows(p, self._build_result())
            text = p.read_text()
        self.assertIn("Concrete_bulk_modulus", text)
        self.assertIn("25.3000", text)
        self.assertIn("Concrete_cylinder_strength", text)

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "EffectiveModuli.csv"
            p.write_text(_SAMPLE_EFFECTIVE)
            result = self._build_result()
            append_concrete_rows(p, result)
            append_concrete_rows(p, result)  # second call should no-op
            # Count occurrences of a uniquely-appended key
            count = p.read_text().count("Concrete_bulk_modulus")
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# Tests: run_and_append end-to-end in a temp directory
# ---------------------------------------------------------------------------


class TestRunAndAppend(unittest.TestCase):
    def _make_operation_dir(self, td: str, with_itz: bool = True) -> Path:
        p = Path(td) / "elastic"
        p.mkdir(parents=True)
        (p / "EffectiveModuli.csv").write_text(_SAMPLE_EFFECTIVE)
        if with_itz:
            (p / "ITZModuli.csv").write_text(_SAMPLE_ITZ)
        return p

    def test_paste_only_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            op = self._make_operation_dir(td, with_itz=False)
            result = run_and_append(op)
        # Paste-only: concrete moduli should equal paste moduli
        self.assertAlmostEqual(result.concrete_bulk_gpa, 12.3, places=3)
        self.assertAlmostEqual(result.concrete_shear_gpa, 8.1, places=3)
        self.assertEqual(result.aggregate_volume_fraction, 0.0)

    def test_writes_log_and_appends_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            op = self._make_operation_dir(td, with_itz=True)
            psd_file = op / "cement_psd.csv"
            psd_file.write_text(_SAMPLE_PSD)

            fine = AggregateSource(
                volume_fraction=0.40,
                bulk_modulus_gpa=37.0,
                shear_modulus_gpa=44.0,
                grading=[(2.0, 0.3), (1.0, 0.4), (0.5, 0.3)],
            )

            result = run_and_append(
                elastic_output_dir=op,
                fine=fine,
                coarse=None,
                cement_psd_path=psd_file,
                air_volume_fraction=0.02,
            )

            effective_text = (op / "EffectiveModuli.csv").read_text()
            log_text = (op / "ConcelasLog.txt").read_text()

        self.assertIn("Concrete_bulk_modulus", effective_text)
        self.assertIn("ITZ_bulk_modulus", effective_text)
        self.assertGreater(result.concrete_bulk_gpa, 12.3)
        self.assertIn("GPa", log_text)

    def test_itz_with_no_aggregate_falls_back_to_paste(self) -> None:
        """ITZ file present but caller supplies no aggregate -> concrete = paste."""
        with tempfile.TemporaryDirectory() as td:
            op = self._make_operation_dir(td, with_itz=True)
            result = run_and_append(op, fine=None, coarse=None)
        self.assertAlmostEqual(result.concrete_bulk_gpa, 12.3, places=3)
        self.assertAlmostEqual(result.aggregate_volume_fraction, 0.0)

    def test_missing_effective_moduli_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            op = Path(td) / "elastic"
            op.mkdir(parents=True)
            with self.assertRaises(MissingInputError):
                run_and_append(op)

    def test_aggregate_supplied_but_no_itz_logs_warning(self) -> None:
        """Degraded mode: aggregate supplied but ITZModuli.csv missing -> still runs."""
        with tempfile.TemporaryDirectory() as td:
            op = self._make_operation_dir(td, with_itz=False)
            fine = AggregateSource(
                volume_fraction=0.30,
                bulk_modulus_gpa=37.0,
                shear_modulus_gpa=44.0,
                grading=[(1.0, 1.0)],
            )
            # Should not raise, should use paste moduli as ITZ proxy
            result = run_and_append(op, fine=fine, coarse=None,
                                    air_volume_fraction=0.0)
        self.assertGreater(result.concrete_bulk_gpa, 12.3)


if __name__ == "__main__":
    unittest.main()

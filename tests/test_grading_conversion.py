#!/usr/bin/env python3
"""
Tests for the grading editor's % passing <-> % retained conversion.

Gradings are entered as cumulative % passing and stored as individual
% retained; these functions in widgets/grading_curve.py do the conversion.

Run with: python -m pytest tests/test_grading_conversion.py -v
Or simply: python tests/test_grading_conversion.py
"""

import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.widgets.grading_curve import (
    passing_to_retained,
    retained_to_passing,
    validate_passing,
)

# C 33 fine aggregate, mid-band of the limits (% passing); 9.5 mm is 100
C33_FINE_MID_PASSING = [(4.75, 97.5), (2.36, 90.0), (1.18, 67.5), (0.6, 42.5),
                        (0.3, 17.5), (0.15, 5.0), (0.075, 0.0)]
# The same grading as stored by the 20261117_01 migration (% retained)
C33_FINE_MID_RETAINED = [(4.75, 2.5), (2.36, 7.5), (1.18, 22.5), (0.6, 25.0),
                         (0.3, 25.0), (0.15, 12.5), (0.075, 5.0)]


def assert_points_close(test, actual, expected):
    test.assertEqual([s for s, _ in actual], [s for s, _ in expected])
    for (_, a), (_, e) in zip(actual, expected):
        test.assertAlmostEqual(a, e, places=9)


class TestPassingToRetained(unittest.TestCase):

    def test_c33_mid_band_matches_migration(self):
        assert_points_close(self, passing_to_retained(C33_FINE_MID_PASSING),
                            C33_FINE_MID_RETAINED)

    def test_input_order_does_not_matter(self):
        shuffled = list(reversed(C33_FINE_MID_PASSING))
        assert_points_close(self, passing_to_retained(shuffled), C33_FINE_MID_RETAINED)

    def test_excess_above_top_sieve_counts_on_top_sieve(self):
        # 97.5 % passing the top sieve: 2.5 % coarser than it goes on it
        result = passing_to_retained([(4.75, 97.5), (2.36, 0.0)])
        assert_points_close(self, result, [(4.75, 2.5), (2.36, 97.5)])

    def test_material_passing_finest_sieve_counts_on_finest(self):
        # 5 % passes 4.75 mm, the finest sieve used, so it is retained on it
        result = passing_to_retained([(25.0, 97.5), (12.5, 42.5), (4.75, 5.0)])
        assert_points_close(self, result, [(25.0, 2.5), (12.5, 55.0), (4.75, 42.5)])

    def test_no57_mid_band_matches_migration(self):
        # #57 mid-band down to No. 16; 0 % passing 1.18 mm leaves no remainder
        result = passing_to_retained([(25.0, 97.5), (12.5, 42.5), (4.75, 5.0),
                                      (2.36, 2.5), (1.18, 0.0)])
        assert_points_close(self, result, [(25.0, 2.5), (12.5, 55.0), (4.75, 37.5),
                                           (2.36, 2.5), (1.18, 2.5)])

    def test_always_sums_to_100(self):
        for points in ([(1.0, 50.0)], [(4.75, 100.0), (0.15, 30.0)],
                       C33_FINE_MID_PASSING):
            total = sum(v for _, v in passing_to_retained(points))
            self.assertAlmostEqual(total, 100.0, places=9)

    def test_single_sieve_holds_everything(self):
        assert_points_close(self, passing_to_retained([(2.36, 40.0)]), [(2.36, 100.0)])


class TestRetainedToPassing(unittest.TestCase):

    def test_c33_round_trip(self):
        assert_points_close(self, retained_to_passing(C33_FINE_MID_RETAINED),
                            C33_FINE_MID_PASSING)
        assert_points_close(
            self, passing_to_retained(retained_to_passing(C33_FINE_MID_RETAINED)),
            C33_FINE_MID_RETAINED)

    def test_total_below_100_leaves_remainder_passing_finest_sieve(self):
        # A sieve analysis that omits the pan: the missing 1 % passed 0.075 mm.
        # (FineAdjust.gdg, 2026-11-18: rescaling turned 97.5 into 97.47.)
        fine_adjust = [(4.75, 2.5), (2.36, 7.5), (1.18, 22.5), (0.6, 25.0),
                       (0.3, 25.0), (0.15, 12.5), (0.075, 4.0)]
        assert_points_close(self, retained_to_passing(fine_adjust),
                            [(4.75, 97.5), (2.36, 90.0), (1.18, 67.5), (0.6, 42.5),
                             (0.3, 17.5), (0.15, 5.0), (0.075, 1.0)])

    def test_total_above_100_is_rescaled(self):
        # Would otherwise give negative % passing (e.g. the old 250 % test row)
        result = retained_to_passing([(2.0, 30.0), (1.0, 120.0)])
        assert_points_close(self, result, [(2.0, 80.0), (1.0, 0.0)])

    def test_zero_rows_above_material_show_100(self):
        result = retained_to_passing([(4.0, 0.0), (2.0, 50.0), (1.0, 50.0)])
        assert_points_close(self, result, [(4.0, 100.0), (2.0, 50.0), (1.0, 0.0)])

    def test_empty_or_zero_total_gives_nothing(self):
        self.assertEqual(retained_to_passing([]), [])
        self.assertEqual(retained_to_passing([(1.0, 0.0)]), [])


class TestValidatePassing(unittest.TestCase):

    def test_valid_table(self):
        self.assertIsNone(validate_passing(C33_FINE_MID_PASSING))

    def test_empty_table(self):
        self.assertIn("at least one sieve", validate_passing([]))

    def test_out_of_range(self):
        self.assertIn("between 0 and 100", validate_passing([(1.18, 101.0)]))
        self.assertIn("between 0 and 100", validate_passing([(1.18, -1.0)]))

    def test_rise_on_finer_sieve(self):
        message = validate_passing([(2.36, 50.0), (1.18, 60.0)])
        self.assertIn("1.18", message)
        self.assertIn("cannot increase", message)

    def test_equal_values_allowed(self):
        self.assertIsNone(validate_passing([(2.36, 50.0), (1.18, 50.0)]))


if __name__ == '__main__':
    unittest.main(verbosity=2)

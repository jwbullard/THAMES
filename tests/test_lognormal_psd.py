#!/usr/bin/env python3
"""
Tests for the log-normal PSD discretization used for micgen input and
cement_psd.csv (MicgenInputService._discretize_log_normal).

Until alpha-4.3 the classes came from the density per um at the class
centers, which made the PSD far too fine (d50 0.74 um for median 10 um,
sigma 2). These tests check the classes against the analytic distribution.

Run with: python -m pytest tests/test_lognormal_psd.py -v
Or simply: python tests/test_lognormal_psd.py
"""

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.stats import lognorm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.micgen_input_service import MicgenInputService

CASES = [(10.0, 2.0), (5.0, 0.5), (12.0, 1.0), (15.0, 0.5)]


def discretize(median, sigma):
    # The method does not use instance state
    return MicgenInputService._discretize_log_normal(None, median, sigma)


def d50_from_classes(classes):
    """Median from the cumulative volume at the class edges (log interpolation)."""
    d = np.array([c[0] for c in classes])
    f = np.array([c[1] for c in classes])
    upper = np.append(np.sqrt(d[1:] * d[:-1]), np.inf)  # upper edge of each class
    cumulative = np.cumsum(f)
    i = int(np.searchsorted(cumulative, 0.5))
    lo_c = cumulative[i - 1] if i > 0 else 0.0
    lo_d = upper[i - 1] if i > 0 else d[0]
    t = (0.5 - lo_c) / (cumulative[i] - lo_c)
    return float(np.exp(np.log(lo_d) + t * (np.log(upper[i]) - np.log(lo_d))))


class TestLogNormalDiscretization(unittest.TestCase):

    def test_fractions_sum_to_one(self):
        for median, sigma in CASES:
            total = sum(f for _, f in discretize(median, sigma))
            self.assertAlmostEqual(total, 1.0, places=5, msg=(median, sigma))

    def test_median_matches_analytic(self):
        for median, sigma in CASES:
            self.assertAlmostEqual(d50_from_classes(discretize(median, sigma)) / median,
                                   1.0, delta=0.02, msg=(median, sigma))

    def test_each_class_holds_the_cdf_difference(self):
        classes = discretize(10.0, 1.0)
        d = np.array([c[0] for c in classes])
        edges = np.sqrt(d[1:] * d[:-1])
        expected = np.diff(lognorm.cdf(edges, s=1.0, scale=10.0))
        actual = np.array([c[1] for c in classes])[1:-1]
        np.testing.assert_allclose(actual, expected, atol=1e-9)

    def test_broad_cement_peaks_near_median_not_at_finest_class(self):
        # The pre-4.3 bug made sigma = 2 decrease monotonically from 0.25 um
        classes = discretize(10.0, 2.0)
        fractions = [f for _, f in classes]
        self.assertNotEqual(int(np.argmax(fractions)), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

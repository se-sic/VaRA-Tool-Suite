"""Test example file that can be used as orientation."""
import unittest

import pandas as pd
from pandas import testing

from varats.data.metrics import (
    lorenz_curve,
    gini_coefficient,
    normalized_gini_coefficient,
)


class TestLorenzCurve(unittest.TestCase):
    """Test the ``lorenz_curve`` metric."""

    def test_lorenz_curve(self):
        """Test lorenz curve."""
        data = pd.Series([1, 2, 3, 4, 5])
        expected = pd.Series([1 / 15, 3 / 15, 6 / 15, 10 / 15, 1])

        testing.assert_series_equal(expected, lorenz_curve(data))

    def test_lorenz_curve_perfect_equality(self):
        """Test perfect equality case."""
        data = pd.Series([1, 1, 1, 1])
        expected = pd.Series([0.25, 0.5, 0.75, 1])

        testing.assert_series_equal(expected, lorenz_curve(data))

    def test_lorenz_curve_perfect_inequality(self):
        """Test perfect inequality case."""
        data = pd.Series([0, 0, 0, 1])
        expected = pd.Series([0.0, 0.0, 0.0, 1.0])

        testing.assert_series_equal(expected, lorenz_curve(data))


class TestGiniCoefficient(unittest.TestCase):
    """Test the ``gini_coefficient`` metric."""

    def test_gini(self):
        """Test gini coefficient."""
        data = pd.Series([1, 2, 3, 4])
        expected = 0.25

        self.assertEqual(expected, gini_coefficient(data))

    def test_gini_perfect_equality(self):
        """Test perfect equality case."""
        data = pd.Series([1, 1, 1, 1])

        self.assertEqual(0, gini_coefficient(data))

    def test_gini_perfect_inequality(self):
        """Test perfect inequality case."""
        data = pd.Series([0, 0, 0, 1])
        expected = 1 - 1 / len(data)

        self.assertEqual(expected, gini_coefficient(data))


class TestNormalizedGiniCoefficient(unittest.TestCase):
    """Test the ``normalized_gini_coefficient`` metric."""

    def test_normalized_gini(self):
        """Test normalized gini coefficient."""
        data = pd.Series([1, 2, 3, 4])
        expected = 1 / 3

        self.assertEqual(expected, normalized_gini_coefficient(data))

    def test_normalized_gini_perfect_equality(self):
        """Test perfect equality case."""
        data = pd.Series([1, 1, 1, 1])

        self.assertEqual(0, normalized_gini_coefficient(data))

    def test_normalized_gini_perfect_inequality(self):
        """Test perfect inequality case."""
        data = pd.Series([0, 0, 0, 1])
        expected = 1

        self.assertEqual(expected, normalized_gini_coefficient(data))

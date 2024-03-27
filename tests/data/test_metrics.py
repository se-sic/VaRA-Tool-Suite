"""Test example file that can be used as orientation."""
import math
import typing as tp
import unittest

import pandas as pd
from pandas import testing

from varats.data.metrics import (
    lorenz_curve,
    gini_coefficient,
    normalized_gini_coefficient,
    ConfusionMatrix,
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

    def test_normalized_gini_for_one_value(self):
        """Test if normalized gini works if we only have one value."""
        data_only_one = pd.Series([42])
        expected = 0

        self.assertEqual(expected, normalized_gini_coefficient(data_only_one))


class TestClassificationResults(unittest.TestCase):
    """Test if the classification metrics are correctly calculated."""

    all_good: ConfusionMatrix
    all_bad: ConfusionMatrix
    balanced_50_50: ConfusionMatrix
    skewed_positiv_entries: ConfusionMatrix
    skewed_negative_entries: ConfusionMatrix

    @classmethod
    def setUpClass(cls) -> None:
        cls.all_good = ConfusionMatrix([1, 2, 3], [4, 5, 6], [1, 2, 3],
                                       [4, 5, 6])

        cls.all_bad = ConfusionMatrix([1, 2, 3], [4, 5, 6], [4, 5, 6],
                                      [1, 2, 3])
        cls.balanced_50_50 = ConfusionMatrix([1, 2, 3, 4], [5, 6, 7, 8],
                                             [1, 2, 5, 6], [3, 4, 7, 8])

        cls.skewed_positiv_entries = ConfusionMatrix([2, 3, 4, 5, 6, 7, 8, 9],
                                                     [1], [3, 4, 5, 6, 7, 8, 9],
                                                     [1, 2])
        cls.skewed_negative_entries = ConfusionMatrix([1],
                                                      [2, 3, 4, 5, 6, 7, 8, 9],
                                                      [1, 2],
                                                      [3, 4, 5, 6, 7, 8, 9])

    def test_true_positive(self) -> None:
        """Test if true positives are correctly calculated."""
        self.assertEqual(self.all_good.TP, 3)
        self.assertEqual(self.all_bad.TP, 0)
        self.assertEqual(self.balanced_50_50.TP, 2)
        self.assertEqual(self.skewed_positiv_entries.TP, 7)
        self.assertEqual(self.skewed_negative_entries.TP, 1)

    def test_false_positive(self) -> None:
        """Test if false positives are correctly calculated."""
        self.assertEqual(self.all_good.FP, 0)
        self.assertEqual(self.all_bad.FP, 3)
        self.assertEqual(self.balanced_50_50.FP, 2)
        self.assertEqual(self.skewed_positiv_entries.FP, 0)
        self.assertEqual(self.skewed_negative_entries.FP, 1)

    def test_true_negative(self) -> None:
        """Test if true negatives are correctly calculated."""
        self.assertEqual(self.all_good.TN, 3)
        self.assertEqual(self.all_bad.TN, 0)
        self.assertEqual(self.balanced_50_50.TN, 2)
        self.assertEqual(self.skewed_positiv_entries.TN, 1)
        self.assertEqual(self.skewed_negative_entries.TN, 7)

    def test_false_negative(self) -> None:
        """Test if false negatives are correctly calculated."""
        self.assertEqual(self.all_good.FN, 0)
        self.assertEqual(self.all_bad.FN, 3)
        self.assertEqual(self.balanced_50_50.FN, 2)
        self.assertEqual(self.skewed_positiv_entries.FN, 1)
        self.assertEqual(self.skewed_negative_entries.FN, 0)

    def test_true_positive_values(self) -> None:
        """Test if true positive values are correctly calculated."""
        self.assertSetEqual(self.all_good.getTPs(), {1, 2, 3})
        self.assertSetEqual(self.all_bad.getTPs(), set())
        self.assertSetEqual(self.balanced_50_50.getTPs(), {1, 2})
        self.assertSetEqual(
            self.skewed_positiv_entries.getTPs(), {3, 4, 5, 6, 7, 8, 9}
        )
        self.assertSetEqual(self.skewed_negative_entries.getTPs(), {1})

    def test_true_negative_values(self) -> None:
        """Test if true negatives values are correctly calculated."""
        self.assertSetEqual(self.all_good.getTNs(), {4, 5, 6})
        self.assertSetEqual(self.all_bad.getTNs(), set())
        self.assertSetEqual(self.balanced_50_50.getTNs(), {7, 8})
        self.assertSetEqual(self.skewed_positiv_entries.getTNs(), {1})
        self.assertSetEqual(
            self.skewed_negative_entries.getTNs(), {3, 4, 5, 6, 7, 8, 9}
        )

    def test_false_positive_values(self) -> None:
        """Test if false positive values are correctly calculated."""
        self.assertSetEqual(self.all_good.getFPs(), set())
        self.assertSetEqual(self.all_bad.getFPs(), {4, 5, 6})
        self.assertSetEqual(self.balanced_50_50.getFPs(), {5, 6})
        self.assertSetEqual(self.skewed_positiv_entries.getFPs(), set())
        self.assertSetEqual(self.skewed_negative_entries.getFPs(), {2})

    def test_false_negative_values(self) -> None:
        """Test if false negatives values are correctly calculated."""
        self.assertSetEqual(self.all_good.getFNs(), set())
        self.assertSetEqual(self.all_bad.getFNs(), {1, 2, 3})
        self.assertSetEqual(self.balanced_50_50.getFNs(), {3, 4})
        self.assertSetEqual(self.skewed_positiv_entries.getFNs(), {2})
        self.assertSetEqual(self.skewed_negative_entries.getFNs(), set())

    def test_precision(self) -> None:
        """Test if precision are correctly calculated."""
        self.assertEqual(self.all_good.precision(), 1.0)
        self.assertEqual(self.all_bad.precision(), 0.0)
        self.assertEqual(self.balanced_50_50.precision(), 0.5)
        self.assertEqual(self.skewed_positiv_entries.precision(), 1.0)
        self.assertEqual(self.skewed_negative_entries.precision(), 0.5)

    def test_recall(self) -> None:
        """Test if recall are correctly calculated."""
        self.assertEqual(self.all_good.recall(), 1.0)
        self.assertEqual(self.all_bad.recall(), 0.0)
        self.assertEqual(self.balanced_50_50.recall(), 0.5)
        self.assertEqual(self.skewed_positiv_entries.recall(), 0.875)
        self.assertEqual(self.skewed_negative_entries.recall(), 1.0)

    def test_specificity(self) -> None:
        """Test if specificity are correctly calculated."""
        self.assertEqual(self.all_good.specificity(), 1.0)
        self.assertEqual(self.all_bad.specificity(), 0.0)
        self.assertEqual(self.balanced_50_50.specificity(), 0.5)
        self.assertEqual(self.skewed_positiv_entries.specificity(), 1.0)
        self.assertEqual(self.skewed_negative_entries.specificity(), 0.875)

    def test_accuracy(self) -> None:
        """Test if accuracy are correctly calculated."""
        self.assertEqual(self.all_good.accuracy(), 1.0)
        self.assertEqual(self.all_bad.accuracy(), 0.0)
        self.assertEqual(self.balanced_50_50.accuracy(), 0.5)
        self.assertAlmostEqual(
            self.skewed_positiv_entries.accuracy(), 0.88888888, places=7
        )
        self.assertAlmostEqual(
            self.skewed_negative_entries.accuracy(), 0.88888888, places=7
        )

    def test_balanced_accuracy(self) -> None:
        """Test if balanced_accuracy are correctly calculated."""
        self.assertEqual(self.all_good.balanced_accuracy(), 1.0)
        self.assertEqual(self.all_bad.balanced_accuracy(), 0.0)
        self.assertEqual(self.balanced_50_50.balanced_accuracy(), 0.5)
        self.assertAlmostEqual(
            self.skewed_positiv_entries.balanced_accuracy(), 0.9375, places=4
        )
        self.assertAlmostEqual(
            self.skewed_negative_entries.balanced_accuracy(), 0.9375, places=4
        )

    def test_f1_score(self) -> None:
        """Test if f1 score are correctly calculated."""
        self.assertEqual(self.all_good.f1_score(), 1.0)
        self.assertEqual(self.all_bad.f1_score(), 0.0)
        self.assertEqual(self.balanced_50_50.f1_score(), 0.5)
        self.assertAlmostEqual(
            self.skewed_positiv_entries.f1_score(), 0.93333333, places=7
        )
        self.assertAlmostEqual(
            self.skewed_negative_entries.f1_score(), 0.66666666, places=7
        )

    def test_no_positive_values(self) -> None:
        """Test if call metrics are correctly calculated even without positive
        values."""
        empty: tp.List[int] = []
        conf_matrix = ConfusionMatrix(empty, [4, 5, 6], empty, [4, 5, 6])

        self.assertTrue(math.isnan(conf_matrix.precision()))
        self.assertTrue(math.isnan(conf_matrix.recall()))
        self.assertEqual(conf_matrix.specificity(), 1.0)
        self.assertEqual(conf_matrix.accuracy(), 1.0)
        self.assertTrue(math.isnan(conf_matrix.balanced_accuracy()))
        self.assertTrue(math.isnan(conf_matrix.f1_score()))

    def test_no_true_positive_values(self) -> None:
        """Test if call metrics are correctly calculated even without positive
        values."""
        empty: tp.List[int] = []
        conf_matrix = ConfusionMatrix(empty, [4, 5, 6], [1, 2, 3], [4, 5, 6])

        self.assertEqual(conf_matrix.precision(), 0.0)
        self.assertTrue(math.isnan(conf_matrix.recall()))
        self.assertEqual(conf_matrix.specificity(), 1.0)
        self.assertEqual(conf_matrix.accuracy(), 1.0)
        self.assertTrue(math.isnan(conf_matrix.balanced_accuracy()))
        self.assertEqual(conf_matrix.f1_score(), 0.0)

    def test_no_pred_positive_values(self) -> None:
        """Test if call metrics are correctly calculated even without positive
        values."""
        empty: tp.List[int] = []
        conf_matrix = ConfusionMatrix([1, 2, 3], [4, 5, 6], empty, [4, 5, 6])

        self.assertTrue(math.isnan(conf_matrix.precision()))
        self.assertEqual(conf_matrix.recall(), 0.0)
        self.assertEqual(conf_matrix.specificity(), 1.0)
        self.assertEqual(conf_matrix.accuracy(), 0.5)
        self.assertEqual(conf_matrix.balanced_accuracy(), 0.5)
        self.assertTrue(math.isnan(conf_matrix.f1_score()))

    def test_stringify(self) -> None:
        """Test if we correctly print a ConfusionMatrix."""
        self.assertEqual(
            str(self.all_good), """ConfM[TP=3, TN=3, FP=0, FN=0]
  ├─ Precision: 1.0
  ├─ Recall:    1.0
  ├─ Accuracy:  1.0
  └─ F1_Score:  1.0
"""
        )

"""Tests that the report utility functions work as expected."""
import unittest

from varats.data.reports.reports_util import (
    feature_region_string_from_set,
    extract_feature_region_set_from_string,
)


class TestFeatureReportUtils(unittest.TestCase):
    """Tests utility functions for feature reports."""

    def test_extract_single_feature(self) -> None:
        self.assertEqual({"feature1"},
                         extract_feature_region_set_from_string("FR(feature1)"))
        self.assertEqual({"A"}, extract_feature_region_set_from_string("FR(A)"))

    def test_extract_two_features(self) -> None:
        self.assertEqual({
            "feature1", "feature2"
        }, extract_feature_region_set_from_string("FR(feature1,feature2)"))
        self.assertEqual({"A", "B"},
                         extract_feature_region_set_from_string("FR(A,B)"))

    def test_extract_multiple_features(self) -> None:
        self.assertEqual({"feature1", "feature2", "feature3"},
                         extract_feature_region_set_from_string(
                             "FR(feature1,feature2,feature3)"
                         ))
        self.assertEqual({"A", "B", "C"},
                         extract_feature_region_set_from_string("FR(A,B,C)"))
        self.assertEqual({
            "A", "B", "C", "D", "E", "F", "G", "H"
        }, extract_feature_region_set_from_string("FR(A,B,C,D,E,F,G,H)"))

    def test_single_feature_to_string(self) -> None:
        self.assertEqual(
            "FR(feature1)", feature_region_string_from_set({"feature1"})
        )
        self.assertEqual("FR(A)", feature_region_string_from_set({"A"}))

    def test_two_features_to_string(self) -> None:
        self.assertEqual(
            "FR(feature1,feature2)",
            feature_region_string_from_set({"feature1", "feature2"})
        )
        self.assertEqual("FR(A,B)", feature_region_string_from_set({"A", "B"}))

    def test_multiple_features_to_string(self) -> None:
        self.assertEqual(
            "FR(feature1,feature2,feature3)",
            feature_region_string_from_set({"feature1", "feature2", "feature3"})
        )
        self.assertEqual(
            "FR(A,B,C)", feature_region_string_from_set({"A", "B", "C"})
        )
        self.assertEqual(
            "FR(A,B,C,D,E,F,G,H)",
            feature_region_string_from_set({
                "A", "B", "C", "D", "E", "F", "G", "H"
            })
        )

import unittest
from pathlib import Path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)


class TestTEFIdentifierReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_report = TEFFeatureIdentifierReport(
            Path(TEST_INPUTS_DIR / "TEFIdentifierReport/TestReport.json")
        )

    def test_patch_names(self):
        self.assertEqual(5, len(self.test_report.patch_names))
        self.assertSetEqual({"patch1", "patch2", "patch3", "patch4", "patch5"},
                            self.test_report.patch_names)

    def test_regions_by_patch_name(self):
        patch2_regions = self.test_report.regions_for_patch("patch2")

        expected_regions = {(frozenset(["Base"]), 1),
                            (frozenset(["FeatureA"]), 6),
                            (frozenset(["FeatureB"]), 26),
                            (frozenset(["FeatureB", "FeatureC"]), 24)}

        self.assertIsNotNone(patch2_regions)
        self.assertSetEqual(expected_regions, patch2_regions)

    def test_patches_region_contain(self):
        affected_patches = self.test_report.patches_containing_region([
            "FeatureC"
        ])

        expected_patches = [("patch2", frozenset(["FeatureC", "FeatureB"]), 24),
                            ("patch3", frozenset(["FeatureC", "FeatureA"]), 2),
                            ("patch4", frozenset(["FeatureC"]), 1)]

        self.assertCountEqual(expected_patches, affected_patches)

        affected_patches = self.test_report.patches_containing_region([
            "FeatureA"
        ])
        expected_patches = [("patch1", frozenset(["FeatureA"]), 6),
                            ("patch2", frozenset(["FeatureA"]), 6),
                            ("patch3", frozenset(["FeatureC", "FeatureA"]), 2),
                            ("patch3", frozenset(["FeatureA"]), 6),
                            ("patch4", frozenset(["FeatureA"]), 6),
                            ("patch5", frozenset(["FeatureA"]), 6)]

        self.assertCountEqual(expected_patches, affected_patches)

    def test_patches_region_exact(self):
        affected_patches = self.test_report.patches_for_regions(["FeatureC"])
        expected_patches = [("patch4", frozenset(["FeatureC"]), 1)]

        self.assertCountEqual(expected_patches, affected_patches)

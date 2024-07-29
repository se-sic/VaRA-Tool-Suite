import typing as tp
import unittest

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.workload_feature_intensity_report import (
    WorkloadFeatureIntensityReport,
)


class TestWorkloadFeatureIntensityReport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__intensity_test_report = WorkloadFeatureIntensityReport(
            TEST_INPUTS_DIR /
            "results/SynthCTCRTP/WFI-WFIR-SynthCTCRTP-all-3bcb385a47/test-report.zip"
        )

    def __test_feature_intensity(
        self, workload: str, features: tp.List[str], expected_intensity: int
    ):
        intensities = self.__intensity_test_report.feature_intensities_for_binary(
            "test-binary"
        )

        self.assertIn(workload, intensities)
        self.assertEqual(
            intensities[workload][frozenset(features)], expected_intensity
        )

    def __test_region_intensity(
        self, workload: str, features: tp.List[str],
        expected_intensity: tp.List[tp.Tuple[tp.List[int], int]]
    ):
        region_intensities = self.__intensity_test_report.region_intensities_for_binary(
            "test-binary"
        )

        self.assertIn(workload, region_intensities)

        for region_combination, intensity in expected_intensity:
            self.assertEqual(
                region_intensities[workload][frozenset(features)][
                    frozenset(region_combination)], intensity
            )

    def test_binary_detection(self):
        report = WorkloadFeatureIntensityReport(
            TEST_INPUTS_DIR /
            "results/SynthCTCRTP/WFI-WFIR-SynthCTCRTP-all-3bcb385a47/e0eee357-277e-4956-ab2b-2e5cf08ce5c0_config-0_success.zip"
        )

        self.assertListEqual(report.binaries(), ["binary1", "binary2"])

    def test_workload_detection(self):
        report = WorkloadFeatureIntensityReport(
            TEST_INPUTS_DIR /
            "results/SynthCTCRTP/WFI-WFIR-SynthCTCRTP-all-3bcb385a47/e0eee357-277e-4956-ab2b-2e5cf08ce5c0_config-0_success.zip"
        )

        self.assertListEqual(
            report.workloads_for_binary("binary1"),
            [f"b1-workload{i}" for i in range(1, 9)],
            f"Workloads for binary1: {report.workloads_for_binary('binary1')}"
        )
        self.assertListEqual(
            report.workloads_for_binary("binary2"),
            [f"b2-workload{i}" for i in range(1, 9)],
            f"Workloads for binary1: {report.workloads_for_binary('binary1')}"
        )

    def test_workload_invalid_binary(self):
        report = WorkloadFeatureIntensityReport(
            TEST_INPUTS_DIR /
            "results/SynthCTCRTP/WFI-WFIR-SynthCTCRTP-all-3bcb385a47/e0eee357-277e-4956-ab2b-2e5cf08ce5c0_config-0_success.zip"
        )

        self.assertEqual(report.workloads_for_binary("invalid_binary"), [])

    def test_feature_intensity_ignores_base_feature(self):
        self.__test_feature_intensity("onlyA-OneID", ["Base"], 0)
        self.__test_feature_intensity("onlyA-TwoIDs", ["Base"], 0)
        self.__test_feature_intensity("AB-OneID", ["Base"], 0)
        self.__test_feature_intensity("AB-MultIDs", ["Base"], 0)
        self.__test_feature_intensity("AB-overlapping-OneID", ["Base"], 0)
        self.__test_feature_intensity("AB-overlapping-MultIDs", ["Base"], 0)

    def test_feature_intensity_single_region_single_id(self):
        self.__test_feature_intensity("onlyA-OneID", ["FeatureA"], 10)

    def test_region_intensity_single_region_single_id(self):
        workload = "onlyA-OneID"
        features = ["FeatureA"]
        expected_intensity = [
            ([1], 10),
        ]

        self.__test_region_intensity(workload, features, expected_intensity)

    def test_feature_intensity_single_region_multiple_ids(self):
        self.__test_feature_intensity("onlyA-TwoIDs", ["FeatureA"], 8)

    def test_region_intensity_single_region_multiple_ids(self):
        workload = "onlyA-TwoIDs"
        features = ["FeatureA"]
        expected_intensity = [
            ([1], 4),
            ([2], 4),
        ]

        self.__test_region_intensity(workload, features, expected_intensity)

    def test_feature_intensity_multiple_regions_single_ids(self):
        self.__test_feature_intensity("AB-OneID", ["FeatureA"], 8)
        self.__test_feature_intensity("AB-OneID", ["FeatureB"], 4)

    def test_region_intensity_multiple_regions_single_ids(self):
        workload = "AB-OneID"

        self.__test_region_intensity(workload, ["FeatureA"], [([1], 8)])
        self.__test_region_intensity(workload, ["FeatureB"], [([2], 4)])

    def test_feature_intensity_multiple_regions_multiple_ids(self):
        self.__test_feature_intensity("AB-MultIDs", ["FeatureA"], 8)
        self.__test_feature_intensity("AB-MultIDs", ["FeatureB"], 4)

    def test_region_intensity_multiple_regions_multiple_ids(self):
        workload = "AB-MultIDs"

        self.__test_region_intensity(
            workload, ["FeatureA"], [([1], 4), ([2], 3), ([6], 1)]
        )
        self.__test_region_intensity(
            workload, ["FeatureB"], [([3], 1), ([4], 2), ([5], 1)]
        )

    def test_feature_intensity_overlapping_regions_single_id(self):
        self.__test_feature_intensity("AB-overlapping-OneID", ["FeatureA"], 7)
        self.__test_feature_intensity("AB-overlapping-OneID", ["FeatureB"], 5)
        self.__test_feature_intensity(
            "AB-overlapping-OneID", ["FeatureA", "FeatureB"], 2
        )

    def test_region_intensity_overlapping_regions_single_id(self):
        workload = "AB-overlapping-OneID"

        self.__test_region_intensity(workload, ["FeatureA"], [([1], 7)])
        self.__test_region_intensity(workload, ["FeatureB"], [([2], 5)])
        self.__test_region_intensity(
            workload, ["FeatureA", "FeatureB"], [([1, 2], 2)]
        )

    def test_feature_intensity_overlapping_regions_multiple_ids(self):
        self.__test_feature_intensity("AB-overlapping-MultIDs", ["FeatureA"], 7)
        self.__test_feature_intensity("AB-overlapping-MultIDs", ["FeatureB"], 5)
        self.__test_feature_intensity(
            "AB-overlapping-MultIDs", ["FeatureA", "FeatureB"], 2
        )

    def test_region_intensity_overlapping_regions_multiple_ids(self):
        workload = "AB-overlapping-MultIDs"

        self.__test_region_intensity(
            workload, ["FeatureA"], [([1], 4), ([2], 3)]
        )
        self.__test_region_intensity(
            workload, ["FeatureB"], [([3], 2), ([4], 3)]
        )
        self.__test_region_intensity(
            workload, ["FeatureA", "FeatureB"], [([4, 2], 2)]
        )


if __name__ == '__main__':
    unittest.main()

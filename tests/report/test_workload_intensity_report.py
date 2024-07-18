import unittest

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.workload_feature_intensity_report import (
    WorkloadFeatureIntensityReport,
)


class TestWorkloadFeatureIntensityReport(unittest.TestCase):

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

        self.assertEqual(
            report.workloads_for_binary("binary1"),
            [f"b1_workload{i}" for i in range(1, 9)]
        )
        self.assertEqual(
            report.workloads_for_binary("binary2"),
            [f"b2_workload{i}" for i in range(1, 9)]
        )


if __name__ == '__main__':
    unittest.main()

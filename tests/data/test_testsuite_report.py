import unittest
from pathlib import Path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.testsuite_report import TestsuiteReport
from varats.utils.testsuite_utils import TestResult


class TestTestsuiteReport(unittest.TestCase):
    """Test TestsuiteReport functionality."""

    report: TestsuiteReport

    @classmethod
    def setUpClass(cls):
        loaded_report = TestsuiteReport(
            Path(TEST_INPUTS_DIR / "reports" / "fake_testsuite_report.json")
        )
        cls.report = loaded_report

    def test_get_results(self):
        """Test if we get the correct test results."""
        results = self.report.results

        self.assertEqual(len(results), 3)
        self.assertEqual(results["test_case_1"], TestResult.PASSED)
        self.assertEqual(results["test_case_2"], TestResult.FAILED)
        self.assertEqual(results["test_case_3"], TestResult.SKIPPED)

    def test_load_results_from_report(self):
        """Test if we can load results from a report file."""
        report_path = Path(
            TEST_INPUTS_DIR / "reports" / "fake_testsuite_report.json"
        )
        loaded_results = TestsuiteReport.load_results_from_report(report_path)

        self.assertEqual(len(loaded_results), 3)
        self.assertEqual(loaded_results["test_case_1"], TestResult.PASSED)
        self.assertEqual(loaded_results["test_case_2"], TestResult.FAILED)
        self.assertEqual(loaded_results["test_case_3"], TestResult.SKIPPED)

    def test_create_report_from_results(self):
        """Test if we can create a report from test results."""
        test_results = {
            "test_case_1": TestResult.PASSED,
            "test_case_2": TestResult.FAILED,
            "test_case_3": TestResult.SKIPPED,
            "test_case_4": TestResult.TIMEOUT,
            "test_case_5": TestResult.DISABLED,
            "test_case_6": TestResult.UNKNOWN,
        }
        report_path = Path(
            TEST_INPUTS_DIR / "reports" / "created_testsuite_report.json"
        )
        TestsuiteReport.create_report_from_results(test_results, report_path)

        loaded_report = TestsuiteReport(report_path)
        self.assertEqual(
            loaded_report.results, {
                "test_case_1": TestResult.PASSED,
                "test_case_2": TestResult.FAILED,
                "test_case_3": TestResult.SKIPPED,
                "test_case_4": TestResult.TIMEOUT,
                "test_case_5": TestResult.DISABLED,
                "test_case_6": TestResult.UNKNOWN,
            }
        )

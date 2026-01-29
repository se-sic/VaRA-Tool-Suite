import unittest
from pathlib import Path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.testsuite_report import TestsuiteReport


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
        self.assertEqual(results["test_case_1"].name, "PASSED")
        self.assertEqual(results["test_case_2"].name, "FAILED")
        self.assertEqual(results["test_case_3"].name, "SKIPPED")

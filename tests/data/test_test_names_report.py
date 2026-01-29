import unittest
from pathlib import Path

from tests.helper_utils import TEST_INPUTS_DIR
from varats.data.reports.test_names_report import TestNamesReport

# import unittest.mock as mock


class TestTestNamesReport(unittest.TestCase):
    """Test TestNamesReport functionality."""
    report: TestNamesReport

    @classmethod
    def setUpClass(cls):
        """Load and parse test names from a preset txt file."""
        loaded_report = TestNamesReport(
            Path(TEST_INPUTS_DIR / "reports" / "fake_test_names.txt")
        )
        cls.report = loaded_report

    def test_get_test_names(self):
        """Test if we get the correct test names."""
        test_names = self.report.test_names

        self.assertEqual(len(test_names), 3)
        self.assertIn("test_case_1", test_names)
        self.assertIn("test_case_2", test_names)
        self.assertIn("test_case_3", test_names)

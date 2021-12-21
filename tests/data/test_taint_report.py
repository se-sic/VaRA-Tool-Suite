"""Test taint propagation reports reports."""

import unittest
from pathlib import Path

from varats.data.reports.taint_report import TaintPropagationReport


class TestTaintPropagationReport(unittest.TestCase):
    """Test taint propagation reports."""

    def test_repr(self) -> None:
        """Check if we repr a report."""
        fake_path_str = "fake_path.txt"
        report = TaintPropagationReport(Path(fake_path_str))

        self.assertEqual(f"TPR: {fake_path_str}", repr(report))

    def test_less_than(self) -> None:
        """Check if we can order reports."""
        report_1 = TaintPropagationReport(Path("fake_path1.txt"))
        report_2 = TaintPropagationReport(Path("fake_path2.txt"))

        self.assertTrue(report_1 < report_2)
        self.assertFalse(report_2 < report_1)

"""Report for testsuite results."""

import json
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport
from varats.utils.testsuite_utils import TestResult


class TestsuiteReport(BaseReport, shorthand="TSR", file_type="json"):
    """Testsuite report."""

    @staticmethod
    def create_report_from_results(
        test_results: dict[str, TestResult], path: Path
    ) -> None:
        """
        Create a testsuite report from test results.

        Args:
            test_results: A dictionary containing test results.
            path: The path where the report should be saved.
        """
        test_results_str: dict[str, str] = {
            name: result.name for name, result in test_results.items()
        }
        with path.open("w") as f:
            json.dump(test_results_str, f, indent=4)

    @staticmethod
    def load_results_from_report(path: Path) -> dict[str, TestResult]:
        """
        Load test results from a testsuite report.

        Args:
            path: The path to the report file.

        Returns:
            A dictionary containing the test results.
        """
        with path.open("r") as f:
            data: dict[str, str] = json.load(f)

        return {test: TestResult[result] for test, result in data.items()}

    def __init__(self, path: Path):
        """Initialize the TestsuiteReport from the given path."""
        super().__init__(path)

        self.__results = self.load_results_from_report(path)

    @property
    def results(self) -> dict[str, TestResult]:
        """
        Get the test results from the report.

        Returns:
            A dictionary containing the test results.
        """
        return self.__results

    @property
    def test_names(self) -> tp.KeysView[str]:
        """Get the names of the tests in the report."""
        return self.__results.keys()

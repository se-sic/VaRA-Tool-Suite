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
        test_results: tp.Dict[str, TestResult], path: Path
    ) -> None:
        """
        Create a testsuite report from test results and save it to the given
        path.

        Args:
            test_results: A dictionary containing test results.
            path: The path where the report should be saved.
        """

        with open(path, 'w') as f:
            json.dump(test_results, f, indent=4)

    @staticmethod
    def load_results_from_report(path: Path) -> tp.Dict[str, TestResult]:
        """
        Load test results from a testsuite report.

        Args:
            path: The path to the report file.
        Returns:
            A dictionary containing the test results.
        """
        with open(path, 'r') as f:
            data: tp.Dict[str, str] = json.load(f)

        return {test: TestResult[result] for test, result in data.items()}

    def __init__(self, path: Path):
        super().__init__(path)

        self.__results = self.load_results_from_report(path)

    @property
    def results(self) -> tp.Dict[str, TestResult]:
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

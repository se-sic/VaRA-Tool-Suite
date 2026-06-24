"""Report for testsuite results."""

import json
import typing as tp
from pathlib import Path

from varats.report.multi_patch_report import MultiPatchReport
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
        test_results_str: tp.Dict[str, str] = {
            name: result.name for name, result in test_results.items()
        }
        with open(path, "w") as f:
            json.dump(test_results_str, f, indent=4)

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

        results: dict[str, TestResult] = {}

        # Test results are inconsistent with either int (as strings) or string values, so we need to handle both cases.
        for test, result in data.items():
            # First, try to convert the result to an int and then to a TestResult enum value.
            try:
                results[test] = TestResult(int(result))
            except:
                # If that fails, try to convert the result directly to a TestResult enum value using the string name.
                try:
                    results[test] = TestResult[result]
                except KeyError:
                    raise ValueError(f"Invalid test result value: {result} for test: {test}")

        # Test results are currently stored as int values in the report, but we want to convert them to TestResult enum values.
        return results
        #return {test: TestResult[result] for test, result in data.items()}

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

class MPTestReport(MultiPatchReport[TestsuiteReport], shorthand="MPTR", file_type="zip"):
    """Multi-patch testsuite report."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TestsuiteReport)

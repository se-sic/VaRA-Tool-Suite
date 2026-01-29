"""Report for capturing test names."""
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport


class TestNamesReport(BaseReport, shorthand="TNR", file_type="txt"):
    """
    Report that captures the names of tests collected from a test suite.

    This report is intended to store the names of tests that were discovered
    during the test collection phase of a test suite execution.
    """

    def __init__(self, path: Path):
        super().__init__(path)

        with open(path, 'r') as f:
            self.__test_names = [line.strip() for line in f.readlines()]

    @property
    def test_names(self) -> tp.List[str]:
        """
        Get the list of test names from the report.

        Returns:
            A list of test names.
        """
        return self.__test_names

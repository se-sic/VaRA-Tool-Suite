"""Plain text report."""
from pathlib import Path

from varats.report.report import BaseReport


class PlainTextReport(BaseReport, shorthand="PTR", file_type="txt"):
    """
    Generic plain text report that can be used to e.g. capture program outputs.

    Does not provide any additional functionality or dedicated parsing.
    """

    def __init__(self, path: Path):
        super().__init__(path)

        with open(path, 'r') as f:
            self.__content = f.read()

    @property
    def text(self) -> str:
        """
        Get the content of the plain text report.

        Returns:
            The content of the report as a string.
        """
        return self.__content

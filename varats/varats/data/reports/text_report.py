"""Plain text report."""
from pathlib import Path

from varats.report.report import BaseReport


class PlainTextReport(BaseReport, shorthand="PTR", file_type="txt"):
    """Plain text report."""

    def __init__(self, path: Path):
        super().__init__(path)
        with open(str(path), "r") as file:
            self.__content = file.read()

    @property
    def content(self) -> str:
        """Get the content of the report."""
        return self.__content

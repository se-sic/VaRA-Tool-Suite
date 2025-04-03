from pathlib import Path

from varats.report.report import BaseReport


class PlainTextReport(BaseReport, shorthand="PTR", file_type="txt"):
    """Plain text report."""

    def __init__(self, path: Path):
        super().__init__(path)

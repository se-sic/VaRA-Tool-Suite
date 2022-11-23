"""Report module for a report containing a single wall-time value."""

import typing as tp
from datetime import timedelta
from pathlib import Path

import numpy as np

from varats.report.report import BaseReport, ReportAggregate


class WallTimeReport(BaseReport, shorthand="WTR", file_type="txt"):
    """Report class containing a single wall-time value."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(self.path, 'r') as stream:
            self.__walltime = timedelta(seconds=float(stream.readline()))

    @property
    def wall_time(self) -> timedelta:
        """Elapsed wall clock time."""
        return self.__walltime

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"{self.__walltime}"


class WallTimeReportAggregate(
    ReportAggregate[WallTimeReport],
    shorthand=WallTimeReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple wall-time reports stored inside a
    zip file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, WallTimeReport)

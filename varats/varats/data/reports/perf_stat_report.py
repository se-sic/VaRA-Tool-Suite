"""Report class for perf stat output."""

import re
from pathlib import Path

import pandas as pd

from varats.report.report import BaseReport, ReportAggregate


class PerfStatReport(BaseReport, shorthand="PERFSTAT", file_type="json"):
    """Converts perf stat output to a dictionary of data."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.df = pd.read_json(path)
        if (
            'interval' in self.df.columns and 'event' in self.df.columns and
            'counter-value' in self.df.columns
        ):
            self.df = self.df.pivot(
                index='interval', columns='event', values='counter-value'
            )
        else:
            print(
                f"Warning: JSON structure in {path} "
                f"might not be in the expected format."
            )


class PerfStatReportAggregate(
    ReportAggregate[PerfStatReport],
    shorthand=PerfStatReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple Perf Stat reports stored inside a
    zip file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfStatReport)

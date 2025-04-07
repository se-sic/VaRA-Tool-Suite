import json
import re
import typing as tp
import zipfile
from pathlib import Path

import chardet
import pandas as pd

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


class PerfStatReport(BaseReport, shorthand="PERFSTAT", file_type="json"):
    """Converts perf stat output to a dictionary of data."""

    def __init__(self, path: Path):
        self.df = pd.read_json(path)
        if 'interval' in self.df.columns and 'event' in self.df.columns and 'counter-value' in self.df.columns:
            self.df = self.df.pivot(
                index='interval', columns='event', values='counter-value'
            )
        else:
            print(
                f"Warning: JSON structure in {path} might not be in the expected format."
            )


class PerfStatReportAggregate(
    ReportAggregate[PerfStatReport],
    shorthand=PerfStatReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple TEF reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, PerfStatReport)


__WORKLOAD_FILE_REGEX = re.compile(r"trace\_(?P<label>.+)$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    if (
        match :=
        __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    ):
        return str(match.group("label"))

    return None

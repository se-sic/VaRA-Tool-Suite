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
        df = pd.DataFrame()
        with open(path, "r") as file:
            data = json.load(file)
            for row in data:
                interval = row['interval']
                event = row['event']
                counter_value = float(row['counter-value'])

                if len(df) == 0:
                    df.loc[interval, event] = counter_value
                if interval not in df.index:
                    df.loc[interval] = pd.Series()
                if event not in df.columns:
                    df[event] = None

                df.loc[interval, event] = counter_value

            self.df = df


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

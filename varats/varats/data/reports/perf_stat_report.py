import re
import typing as tp
import chardet
import zipfile
import pandas as pd

from varats.report.report import BaseReport, ReportAggregate
from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from pathlib import Path


class PerfStatReport(BaseReport, shorthand="PERFSTAT", file_type="csv"):
    """
    Converts perf stat output to a dictionary of data
    """
    def __init__(self, path: Path):
        df = pd.DataFrame() 
        line_counter = 0
        with open(path, "r") as file:
            for line in file:
                line_counter += 1
                if line_counter <= 2:
                    continue
                line = line.strip()
                elements = line.split(',')
                elements = [elem for elem in elements if elem]
                try:
                    int(elements[2])
                    parameter = elements[3]
                except ValueError:
                    parameter = elements[2]
                value = elements[1]
                timestemp = elements[0]
                if parameter not in df.columns:
                    df[parameter] = None
                if timestemp not in df.index:
                    df.loc[timestemp] = None
                df.at[timestemp, parameter] = value

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
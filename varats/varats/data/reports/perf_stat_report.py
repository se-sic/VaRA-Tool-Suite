import re
import typing as tp
import chardet
import zipfile

from varats.report.report import BaseReport, ReportAggregate
from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from pathlib import Path


class PerfStatReport(BaseReport, shorthand="PERFSTAT", file_type="csv"):
    """
    Converts perf stat output to a dictionary of data
    """
    def __init__(self, path: Path):
        data = {}
        parameters = []
        unique_parameters = set()
        line_counter = 0
        with open(path, "r") as file:
            for line in file:
                line_counter += 1
                if line_counter <= 2:
                    continue
                line = line.strip()
                elements = line.split('\t')
                elements = [elem for elem in elements if elem]
                if elements[0] in data.keys():
                    data[elements[0]].append(elements[1])
                else:
                    data[elements[0]] = [elements[1]]
                if elements[2] not in unique_parameters:
                    unique_parameters.add(elements[2])
                    parameters.append(elements[2])
        self.data = data
        self.parameters = parameters


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
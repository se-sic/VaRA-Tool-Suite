"""
Simple report module to create and handle the standard timing output of perf
stat.

Examples to produce a ``LinuxPerfReport``:

    Commandline usage:
        .. code-block:: bash

            export REPORT_FILE="Path/To/MyFile"
            perf stat -x ";" -o $REPORT_FILE -- sleep 2

    Experiment code:
        .. code-block:: python

            from benchbuild.utils.cmd import time, sleep
            report_file = "Path/To/MyFile"
            command = sleep["2"]
            perf("stat", "-x", "';'", "-o", f"{report_file}", "--", command)
"""
import csv
import math
import typing as tp
from pathlib import Path

from varats.report.report import BaseReport, ReportAggregate


class LinuxPerfReport(BaseReport, shorthand="LPR", file_type="txt"):
    """Report class to access perf stat output."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__task_clock = math.nan
        self.__ctx_switches: int = -1
        self.__branch_misses: int = -1

        with open(self.path, 'r', newline="") as stream:
            reader = csv.reader(stream, delimiter=';')
            print(f"{reader=}")

            for row in reader:
                print(f"{row=}")

                if len(row) == 0 or row[0].startswith("#"):
                    continue

                metric_name = self.__metric_name(row)
                if not metric_name:
                    continue

                if metric_name == "task-clock:u":
                    self.__task_clock = float(self.__metric_value(row))
                elif metric_name == "context-switches:u":
                    self.__ctx_switches = int(self.__metric_value(row))
                elif metric_name == "branch-misses:u":
                    self.__branch_misses = int(self.__metric_value(row))

    @staticmethod
    def __metric_value(row: tp.List[tp.Any]) -> tp.Any:
        return row[0]

    @staticmethod
    def __metric_unit(row: tp.List[tp.Any]) -> tp.Any:
        return row[1]

    @staticmethod
    def __metric_name(row: tp.List[tp.Any]) -> str:
        return row[2]

    @property
    def task_clock(self) -> float:
        return self.__task_clock

    @property
    def ctx_switches(self) -> int:
        return self.__ctx_switches

    @property
    def branch_misses(self) -> int:
        return self.__branch_misses

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"""LPR ({self.path})
  ├─ TaskClock:    {self.task_clock}
  ├─ CtxSwitches:  {self.ctx_switches}
  └─ BranchMisses: {self.branch_misses}
"""


class LinuxPerfReportAggregate(
    ReportAggregate[LinuxPerfReport],
    shorthand=LinuxPerfReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Meta report for parsing multiple Linux perf reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, LinuxPerfReport)

    @property
    def clock_times(self) -> tp.List[float]:
        return [report.task_clock for report in self.reports()]

    @property
    def ctx_switches(self) -> tp.List[int]:
        return [report.ctx_switches for report in self.reports()]

    @property
    def branch_misses(self) -> tp.List[int]:
        return [report.branch_misses for report in self.reports()]

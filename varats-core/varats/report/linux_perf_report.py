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
import math
import typing as tp
from pathlib import Path

import numpy as np

from varats.report.report import BaseReport, ReportAggregate


class LinuxPerfReport(BaseReport, shorthand="LPR", file_type="txt"):
    """Report class to access perf stat output."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__elapsed_time = math.nan
        self.__ctx_switches: int = -1
        self.__branch_misses: int = -1

        with open(self.path, 'r', newline="") as stream:
            for line in stream:
                line = line.strip("\n ")
                # print(f"{line=}")

                if line == "" or line.startswith("#"):
                    continue

                if "time elapsed" in line:
                    self.__elapsed_time = self.__parse_elapsed_time(line)

                if "context-switches:u" in line:
                    self.__ctx_switches = self.__parse_ctx_switches(line)

                if "branch-misses:u" in line:
                    self.__branch_misses = self.__parse_branch_misses(line)

            if self.__branch_misses == math.nan:
                raise AssertionError()

    @staticmethod
    def __parse_elapsed_time(line: str) -> float:
        return float(line.split(" ")[0].replace(",", ""))

    @staticmethod
    def __parse_ctx_switches(line: str) -> int:
        return int(line.split(" ")[0].replace(",", ""))

    @staticmethod
    def __parse_branch_misses(line: str) -> int:
        if line.startswith("<not counted>"):
            return np.NaN
        return int(line.split(" ")[0].replace(",", ""))

    @property
    def elapsed_time(self) -> float:
        return self.__elapsed_time

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
  ├─ ElapsedTime:  {self.elapsed_time}
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
    def elapsed_time(self) -> tp.List[float]:
        return [report.elapsed_time for report in self.reports()]

    @property
    def ctx_switches(self) -> tp.List[int]:
        return [report.ctx_switches for report in self.reports()]

    @property
    def branch_misses(self) -> tp.List[int]:
        return [report.branch_misses for report in self.reports()]

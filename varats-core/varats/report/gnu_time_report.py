"""
Simple report module to create and handle the standard timing output of GNU
time.

Examples to produce a ``TimeReport``:

    Commandline usage:
        .. code-block:: bash

            export REPORT_FILE="Path/To/MyFile"
            /usr/bin/time -v -o $REPORT_FILE sleep 2

    Experiment code:
        .. code-block:: python

            from benchbuild.utils.cmd import time, sleep
            report_file = "Path/To/MyFile"
            command_to_measure = sleep["2"]
            time("-v", "-o", f"{report_file}", command_to_measure)
"""

import re
import typing as tp
from datetime import timedelta
from pathlib import Path

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


class WrongTimeReportFormat(Exception):
    """Thrown if a time report could not be parsed."""


class TimeReport(BaseReport, shorthand="TR", file_type="txt"):
    """Report class to access GNU time output."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__filesystem_io = (-1, -1)
        with open(self.path, 'r') as stream:
            for line in stream:
                line = line.strip()

                if line.startswith("Command being timed"):
                    self.__command_name: str = TimeReport._parse_command(line)
                    continue

                if line.startswith("Maximum resident set size"):
                    self.__max_resident_size: int = \
                        TimeReport._parse_max_resident_size(line)
                    continue

                if line.startswith("User time"):
                    self.__user_time = TimeReport._parse_user_time(line)
                    continue

                if line.startswith("System time"):
                    self.__system_time = TimeReport._parse_system_time(line)
                    continue

                if line.startswith("Elapsed (wall clock) time"):
                    self.__wall_clock_time: timedelta = \
                        TimeReport._parse_wall_clock_time(line)
                    continue

                if line.startswith("Major (requiring I/O) page faults"):
                    self.__major_page_faults: int = \
                        TimeReport._parse_major_page_faults(line)
                    continue

                if line.startswith("Minor (reclaiming a frame) page faults"):
                    self.__minor_page_faults: int = \
                        TimeReport._parse_minor_page_faults(line)
                    continue

                if line.startswith("Voluntary context switches"):
                    self.__voluntary_ctx_switches: int = \
                        TimeReport._parse_voluntary_ctx_switches(line)
                    continue

                if line.startswith("Involuntary context switches"):
                    self.__involuntary_ctx_switches: int = \
                        TimeReport._parse_involuntary_ctx_switches(line)
                    continue

                if line.startswith("File system inputs"):
                    self.__filesystem_io = (
                        TimeReport._parse_filesystem_io(line),
                        self.__filesystem_io[1]
                    )
                    continue

                if line.startswith("File system outputs"):
                    self.__filesystem_io = (
                        self.__filesystem_io[0],
                        TimeReport._parse_filesystem_io(line)
                    )
                    continue

    @property
    def command_name(self) -> str:
        """Name of the command that was executed."""
        return self.__command_name

    @property
    def user_time(self) -> timedelta:
        """Measured user time in seconds."""
        return self.__user_time

    @property
    def system_time(self) -> timedelta:
        """Measured system time in seconds."""
        return self.__system_time

    @property
    def wall_clock_time(self) -> timedelta:
        """Elapsed wall clock time."""
        return self.__wall_clock_time

    @property
    def max_res_size(self) -> int:
        """Maximum resident size."""
        return self.__max_resident_size

    @property
    def major_page_faults(self) -> int:
        """Major page faults (require I/O)."""
        return self.__major_page_faults

    @property
    def minor_page_faults(self) -> int:
        """Minor page faults (reclaim a frame)."""
        return self.__minor_page_faults

    @property
    def filesystem_io(self) -> tp.Tuple[int, int]:
        """
        Filesystem inputs/outputs.

        Returns: a tuple of (#inputs, #outputs)
        """
        return self.__filesystem_io

    @property
    def voluntary_ctx_switches(self) -> int:
        """Number of voluntary context switches."""
        return self.__voluntary_ctx_switches

    @property
    def involuntary_ctx_switches(self) -> int:
        """Number of involuntary context switches."""
        return self.__involuntary_ctx_switches

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        str_repr = f"Command: {self.command_name}\n"
        str_repr += f"User time: {self.user_time}\n"
        str_repr += f"System time: {self.system_time}\n"
        str_repr += f"Elapsed wall clock time: {self.wall_clock_time}\n"
        str_repr += f"Max Resident Size (kbytes): {self.max_res_size}\n"
        str_repr += \
            f"Voluntary context switches: {self.voluntary_ctx_switches}\n"
        str_repr += \
            f"Involuntary context switches: {self.involuntary_ctx_switches}"
        return str_repr

    __COMMAND_REGEX = re.compile(r'Command being timed: "(?P<command>.*)"')
    __WALL_CLOCK_REGEX = re.compile(r".*\):(?P<time>.*)")
    __MAXRES_REGEX = re.compile(
        r"Maximum resident set size \((?P<size_type>.*)\): (?P<amount>\d*)"
    )

    @staticmethod
    def _parse_command(line: str) -> str:
        """
        >>> TimeReport._parse_command('Command being timed: "echo"')
        'echo'
        """
        if (match := TimeReport.__COMMAND_REGEX.search(line)):
            return str(match.group("command"))

        raise WrongTimeReportFormat("Could not parse command: ", line)

    @staticmethod
    def _parse_user_time(line: str) -> timedelta:
        """
        >>> import datetime
        >>> TimeReport._parse_user_time("User time (seconds): 42.12")
        datetime.timedelta(seconds=42, microseconds=120000)
        """
        if line.startswith("User time"):
            return timedelta(seconds=float(line.split(":")[1]))

        raise WrongTimeReportFormat("Could not parse user time: ", line)

    @staticmethod
    def _parse_system_time(line: str) -> timedelta:
        """
        >>> import datetime
        >>> TimeReport._parse_system_time("System time (seconds): 42.12")
        datetime.timedelta(seconds=42, microseconds=120000)
        """
        if line.startswith("System time"):
            return timedelta(seconds=float(line.split(":")[1]))

        raise WrongTimeReportFormat("Could not parse system time: ", line)

    @staticmethod
    def _parse_wall_clock_time(line: str) -> timedelta:
        """
        >>> import datetime
        >>> TimeReport._parse_wall_clock_time(\
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 1:42:1.12")
        datetime.timedelta(seconds=6121, microseconds=120000)

        >>> import datetime
        >>> TimeReport._parse_wall_clock_time(\
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 42:1.12")
        datetime.timedelta(seconds=2521, microseconds=120000)
        """
        if (match := TimeReport.__WALL_CLOCK_REGEX.search(line)):
            time_str = str(match.group("time"))
            if time_str.count(":") > 1:
                time_split = time_str.split(":")
                return timedelta(
                    hours=int(time_split[0]),
                    minutes=int(time_split[1]),
                    seconds=float(time_split[2])
                )

            time_split = time_str.split(":")
            return timedelta(
                minutes=int(time_split[0]), seconds=float(time_split[1])
            )

        raise WrongTimeReportFormat("Could not prase wall clock time: ", line)

    @staticmethod
    def _parse_max_resident_size(line: str) -> int:
        """
        >>> TimeReport._parse_max_resident_size(\
                "Maximum resident set size (kbytes): 1804")
        1804
        """

        if (match := TimeReport.__MAXRES_REGEX.search(line)):
            if match.group("size_type") != "kbytes":
                raise AssertionError(
                    "Type confusion when parsing GNU time file"
                )

            return int(match.group("amount"))

        raise WrongTimeReportFormat(
            "Could not parse max resident set size: ", line
        )

    @staticmethod
    def _parse_major_page_faults(line: str) -> int:
        if line.startswith("Major (requiring I/O) page faults"):
            return int(line.split(":")[1])

        raise WrongTimeReportFormat("Could not parse major page faults: ", line)

    @staticmethod
    def _parse_minor_page_faults(line: str) -> int:
        if line.startswith("Minor (reclaiming a frame) page faults"):
            return int(line.split(":")[1])

        raise WrongTimeReportFormat("Could not parse minor page faults: ", line)

    @staticmethod
    def _parse_voluntary_ctx_switches(line: str) -> int:
        if line.startswith("Voluntary context switches"):
            return int(line.split(":")[1])

        raise WrongTimeReportFormat(
            "Could not parse voluntary context switches: ", line
        )

    @staticmethod
    def _parse_involuntary_ctx_switches(line: str) -> int:
        if line.startswith("Involuntary context switches"):
            return int(line.split(":")[1])

        raise WrongTimeReportFormat(
            "Could not parse involuntary context switches: ", line
        )

    @staticmethod
    def _parse_filesystem_io(line: str) -> int:
        if line.startswith("File system "):
            return int(line.split(":")[1])

        raise WrongTimeReportFormat(
            "Could not parse filesystem inputs/outputs: ", line
        )


class TimeReportAggregate(
    ReportAggregate[TimeReport],
    shorthand=TimeReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple time reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReport)
        self._measurements_wall_clock_time = [
            report.wall_clock_time.total_seconds() for report in self.reports()
        ]
        self._measurements_ctx_switches = [
            report.voluntary_ctx_switches + report.involuntary_ctx_switches
            for report in self.reports()
        ]

    @property
    def measurements_wall_clock_time(self) -> tp.List[float]:
        """Wall clock time measurements of all aggregated reports."""
        return self._measurements_wall_clock_time

    @property
    def measurements_ctx_switches(self) -> tp.List[int]:
        """Context switches measurements of all aggregated reports."""
        return self._measurements_ctx_switches

    @property
    def max_resident_sizes(self) -> tp.List[int]:
        return [report.max_res_size for report in self.reports()]

    @property
    def major_page_faults(self) -> tp.List[int]:
        return [report.major_page_faults for report in self.reports()]

    @property
    def minor_page_faults(self) -> tp.List[int]:
        return [report.minor_page_faults for report in self.reports()]

    @property
    def filesystem_io(self) -> tp.List[tp.Tuple[int, int]]:
        return [report.filesystem_io for report in self.reports()]

    @property
    def summary(self) -> str:
        import numpy as np  # pylint: disable=import-outside-toplevel
        return (
            f"num_reports = {len(self.reports())}\n"
            "mean (std) of wall clock time = "
            f"{np.mean(self.measurements_wall_clock_time):.2f}"
            f" ({np.std(self.measurements_wall_clock_time):.2f})\n"
            "mean (std) of context switches = "
            f"{np.mean(self.measurements_ctx_switches):.2f}"
            f" ({np.std(self.measurements_ctx_switches):.2f})\n"
        )


class WLTimeReportAggregate(
    WorkloadSpecificReportAggregate[TimeReport],
    shorthand="WL" + TimeReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple time reports stored inside a zip
    file and grouping them based on the workload they belong to."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReport)

    def measurements_wall_clock_time(self,
                                     workload_name: str) -> tp.List[float]:
        """Wall clock time measurements of all aggregated reports."""
        return [
            report.wall_clock_time.total_seconds()
            for report in self.reports(workload_name)
        ]

    def measurements_ctx_switches(self, workload_name: str) -> tp.List[int]:
        """Context switches measurements of all aggregated reports."""
        return [
            report.voluntary_ctx_switches + report.involuntary_ctx_switches
            for report in self.reports(workload_name)
        ]

    def max_resident_sizes(self, workload_name: str) -> tp.List[int]:
        return [report.max_res_size for report in self.reports(workload_name)]

    def summary(self) -> str:
        return (
            f"num_reports = {len(self.reports())}\n"
            f"num_workloads = {len(self.workload_names())}\n"
        )

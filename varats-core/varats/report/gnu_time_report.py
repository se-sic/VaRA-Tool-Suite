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
from datetime import timedelta
from pathlib import Path
import numpy as np

from varats.report.report import BaseReport, FileStatusExtension, ReportFilename
from varats.utils.util import static_vars


class WrongTimeReportFormat(Exception):
    """Thrown if the time report could not be parsed."""


class TimeReport(BaseReport, shorthand="TR", file_type="txt"):
    """Report class to access GNU time output."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

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

                # print("Not matched: ", line)

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

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        str_repr = f"Command: {self.command_name}\n"
        str_repr += f"User time: {self.user_time}\n"
        str_repr += f"System time: {self.system_time}\n"
        str_repr += f"Elapsed wall clock time: {self.wall_clock_time}\n"
        str_repr += f"Max Resident Size (kbytes): {self.max_res_size}"
        return str_repr

    @staticmethod
    @static_vars(
        COMMAND_REGEX=re.compile(r'Command being timed: "(?P<command>.*)"')
    )
    def _parse_command(line: str) -> str:
        """
        >>> TimeReport._parse_command('Command being timed: "echo"')
        'echo'
        """
        match = TimeReport._parse_command.COMMAND_REGEX.search(line)
        if match:
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
    @static_vars(WALL_CLOCK_REGEX=re.compile(r".*\):(?P<time>.*)"))
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
        match = TimeReport._parse_wall_clock_time.WALL_CLOCK_REGEX.search(line)
        if match:
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
    @static_vars(
        MAXRES_REGEX=re.compile(
            r"Maximum resident set size \((?P<size_type>.*)\): (?P<amount>\d*)"
        )
    )
    def _parse_max_resident_size(line: str) -> int:
        """
        >>> TimeReport._parse_max_resident_size(\
                "Maximum resident set size (kbytes): 1804")
        1804
        """
        match = TimeReport._parse_max_resident_size.MAXRES_REGEX.search(line)

        if match:
            if match.group("size_type") != "kbytes":
                raise AssertionError(
                    "Type confusion when parsing GNU time file"
                )

            return int(match.group("amount"))

        raise WrongTimeReportFormat(
            "Could not parse max resident set size: ", line
        )


class TimeReportAggregate:
    """Groups multiple `TimeReport` and allows us to calculate statistics over
    them and generate a summary."""

    def __init__(self) -> None:
        self.__time_reports = dict[str, list[TimeReport]]()

    def add_report(self, binary_name: str, report: TimeReport) -> None:
        """Adds a `TimeReport`."""
        assert binary_name

        if not binary_name in self.__time_reports.keys():
            self.__time_reports[binary_name] = list[TimeReport]()

        self.__time_reports[binary_name].append(report)

    def binary_names(self):
        return self.__time_reports.keys()

    def mean_runtime(self, binary_name: str):
        """Mean of wall clock time."""
        assert binary_name
        return np.mean([time_report.wall_clock_time.total_seconds() for time_report in self.__time_reports[binary_name]])

    def std_deviation_runtime(self, binary_name: str):
        """Standard deviation of wall clock time."""
        assert binary_name
        return np.std([time_report.wall_clock_time.total_seconds() for time_report in self.__time_reports[binary_name]])

    def min_runtime(self, binary_name: str):
        """Minimum value of wall clock time."""
        assert binary_name
        return np.min([time_report.wall_clock_time.total_seconds() for time_report in self.__time_reports[binary_name]])

    def max_runtime(self, binary_name: str):
        """Maximum value of wall clock time."""
        assert binary_name
        return np.max([time_report.wall_clock_time.total_seconds() for time_report in self.__time_reports[binary_name]])

    def summary(self, binary_name: str) -> str:
        assert binary_name
        return f"mean: {self.mean_runtime(binary_name)}\n" \
            f"std-deviation: {self.std_deviation_runtime(binary_name)}\n" \
            f"min: {self.min_runtime(binary_name)}\n" \
            f"max: {self.max_runtime(binary_name)}"

    def summary_to_file(self, binary_name: str, path: Path) -> None:
        assert binary_name
        with open(path, 'w') as file:
            file.write(self.summary(binary_name))

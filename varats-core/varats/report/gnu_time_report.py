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

import numpy as np

from varats.report.report import BaseReport, ReportAggregate
from varats.utils.util import static_vars


class WrongTimeReportFormat(Exception):
    """Thrown if a time report could not be parsed."""


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


class TimeReportAggregate(
    ReportAggregate[TimeReport],
    shorthand=TimeReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple time reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReport)

    @property
    def wall_clock_times(self) -> tp.List[float]:
        return [
            report.wall_clock_time.total_seconds() for report in self.reports
        ]

    @property
    def mean_wall_clock_time(self) -> float:
        return np.mean(self.wall_clock_times)

    @property
    def std_wall_clock_time(self) -> float:
        return np.std(self.wall_clock_times)

    @property
    def summary(self) -> str:
        return f"num_reports = {len(self.reports)}\n" \
            f"mean(wall_clock_time) = {self.mean_wall_clock_time}\n" \
            f"std(wall_clock_time) = {self.std_wall_clock_time}\n"

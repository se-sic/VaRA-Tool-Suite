"""Test GNUTimeReport."""

import unittest
import unittest.mock as mock
from datetime import timedelta
from pathlib import Path

from varats.report.gnu_time_report import TimeReport, WrongTimeReportFormat

GNU_TIME_OUTPUT_1 = """  Command being timed: "echo"
  User time (seconds): 2.00
  System time (seconds): 3.00
  Percent of CPU this job got: 0%
  Elapsed (wall clock) time (h:mm:ss or m:ss): 0:42.00
  Average shared text size (kbytes): 0
  Average unshared data size (kbytes): 0
  Average stack size (kbytes): 0
  Average total size (kbytes): 0
  Maximum resident set size (kbytes): 1804
  Average resident set size (kbytes): 0
  Major (requiring I/O) page faults: 0
  Minor (reclaiming a frame) page faults: 142
  Voluntary context switches: 1
  Involuntary context switches: 1
  Swaps: 0
  File system inputs: 0
  File system outputs: 0
  Socket messages sent: 0
  Socket messages received: 0
  Signals delivered: 0
  Page size (bytes): 4096
  Exit status: 0
"""


class TestGNUTimeReportParserFunctions(unittest.TestCase):
    """Tests if the GNU time report can be parsed correctly."""

    def test_parse_command(self):
        """Test if we correctly parse the command from the input line."""
        with self.assertRaises(WrongTimeReportFormat):
            TimeReport._parse_command('  Something other timed: "echo"')

    def test_user_time(self):
        """Test if we correctly parse the user time from the input line."""
        with self.assertRaises(WrongTimeReportFormat):
            TimeReport._parse_user_time("  Something other timed:")

    def test_system_time(self):
        """Test if we correctly parse the system time from the input line."""
        with self.assertRaises(WrongTimeReportFormat):
            TimeReport._parse_system_time("  Something other timed:")

    def test_wall_clock_time(self):
        """Test if we correctly parse the wall clock time from the input
        line."""
        with self.assertRaises(WrongTimeReportFormat):
            TimeReport._parse_wall_clock_time("  Something other timed:")

    def test_max_resident_size(self):
        """Test if we correctly parse the max resident size from the input
        line."""
        with self.assertRaises(WrongTimeReportFormat):
            TimeReport._parse_max_resident_size("  Something other timed:")

    def test_max_resident_size_byte_type(self):
        """Test if we correctly parse the max resident size from the input
        line."""
        with self.assertRaises(AssertionError):
            TimeReport._parse_max_resident_size(
                "  Maximum resident set size (mbytes): 1804"
            )


class TestGNUTimeReport(unittest.TestCase):
    """Tests if we can correctly TimeReport values."""

    report: TimeReport

    @classmethod
    def setUpClass(cls):
        """Load GNU time report."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=GNU_TIME_OUTPUT_1)
        ):
            cls.report = TimeReport(Path("fake_file_path"))

    def test_command_name(self):
        """Test if we can extract the command name from the parsed file."""
        self.assertEqual(self.report.command_name, "echo")

    def test_user_time(self):
        """Test if we can extract the user time from the parsed file."""
        self.assertEqual(self.report.user_time, timedelta(seconds=2))

    def test_system_time(self):
        """Test if we can extract the system time from the parsed file."""
        self.assertEqual(self.report.system_time, timedelta(seconds=3))

    def test_repr_str(self):
        """Test string representation of TimeReports."""
        expected_result = """Command: echo
User time: 0:00:02
System time: 0:00:03
Elapsed wall clock time: 0:00:42
Max Resident Size (kbytes): 1804
Voluntary context switches: 1
Involuntary context switches: 1"""
        self.assertEqual(repr(self.report), expected_result)
        self.assertEqual(str(self.report), expected_result)

"""Test LinuxPerfReport."""

import unittest
import unittest.mock as mock
from datetime import timedelta
from pathlib import Path

from varats.report.linux_perf_report import LinuxPerfReport

PERF_REPORT_1 = """# started on Sun Jul 23 16:33:56 2023

0.28;msec;task-clock:u;281620;100.00;0.398;CPUs utilized
0;;context-switches:u;281620;100.00;0.000;/sec
0;;cpu-migrations:u;281620;100.00;0.000;/sec
63;;page-faults:u;281620;100.00;223.706;K/sec
297468;;cycles:u;282100;100.00;1.056;GHz
21086;;stalled-cycles-frontend:u;282100;100.00;7.09;frontend cycles idle
84315;;stalled-cycles-backend:u;282100;100.00;28.34;backend cycles idle
200506;;instructions:u;282100;100.00;0.67;insn per cycle
;;;;;0.42;stalled cycles per insn
48602;;branches:u;282100;100.00;172.580;M/sec
2946;;branch-misses:u;282100;100.00;6.06;of all branches
<not counted>;;L1-dcache-loads:u;0;0.00;;
<not counted>;;L1-dcache-load-misses:u;0;0.00;;
<not supported>;;LLC-loads:u;0;100.00;;
<not supported>;;LLC-load-misses:u;0;100.00;;
"""

PERF_REPORT_2 = """# started on Sun Jul 23 16:36:38 2023

689.70;msec;task-clock:u;689702567;100.00;0.158;CPUs utilized
0;;context-switches:u;689702567;100.00;0.000;/sec
0;;cpu-migrations:u;689702567;100.00;0.000;/sec
2924;;page-faults:u;689702567;100.00;4.240;K/sec
442557352;;cycles:u;513385825;74.00;0.642;GHz
6447861;;stalled-cycles-frontend:u;513968009;74.00;1.46;frontend cycles idle
120234822;;stalled-cycles-backend:u;517763201;75.00;27.17;backend cycles idle
944044714;;instructions:u;519151351;75.00;2.13;insn per cycle
;;;;;0.13;stalled cycles per insn
216559082;;branches:u;517782741;75.00;313.989;M/sec
1542284;;branch-misses:u;517881196;75.00;0.71;of all branches
286757265;;L1-dcache-loads:u;517504374;75.00;415.769;M/sec
9357536;;L1-dcache-load-misses:u;515435585;74.00;3.26;of all L1-dcache accesses
<not supported>;;LLC-loads:u;0;100.00;;
<not supported>;;LLC-load-misses:u;0;100.00;;
"""


class TestLinuxPerfReport(unittest.TestCase):
    """Tests if the Linux perf report can be loaded correctly."""

    report_1: LinuxPerfReport
    report_2: LinuxPerfReport

    @classmethod
    def setUpClass(cls) -> None:
        """Load Linux perf report."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=PERF_REPORT_1)
        ):
            cls.report_1 = LinuxPerfReport(Path("fake_file_path"))

        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=PERF_REPORT_2)
        ):
            cls.report_2 = LinuxPerfReport(Path("fake_file_path"))

    def test_task_clock_parsing(self) -> None:
        """Checks if we correctly parsed the value for task clock."""
        self.assertEqual(self.report_1.task_clock, 0.28)
        self.assertEqual(self.report_2.task_clock, 689.70)

    def test_context_switches_parsing(self) -> None:
        """Checks if we correctly parsed the value for context switches."""
        self.assertEqual(self.report_1.ctx_switches, 0)
        self.assertEqual(self.report_2.ctx_switches, 0)

    def test_branch_misses_parsing(self) -> None:
        """Checks if we correctly parsed the value for branch misses."""
        self.assertEqual(self.report_1.branch_misses, 2946)
        self.assertEqual(self.report_2.branch_misses, 1542284)

"""Test LinuxPerfReport."""

import unittest
import unittest.mock as mock
from datetime import timedelta
from pathlib import Path

from varats.report.linux_perf_report import LinuxPerfReport

PERF_REPORT_1 = """# started on Sun Jul 23 22:51:54 2023


 Performance counter stats for 'echo foo:bar':

              0.30 msec task-clock:u                     #    0.406 CPUs utilized
                 0      context-switches:u               #    0.000 /sec
                 0      cpu-migrations:u                 #    0.000 /sec
                64      page-faults:u                    #  212.723 K/sec
           360,721      cycles:u                         #    1.199 GHz
            26,199      stalled-cycles-frontend:u        #    7.26% frontend cycles idle
           111,008      stalled-cycles-backend:u         #   30.77% backend cycles idle
           200,655      instructions:u                   #    0.56  insn per cycle
                                                  #    0.55  stalled cycles per insn
            48,631      branches:u                       #  161.639 M/sec
             3,012      branch-misses:u                  #    6.19% of all branches
     <not counted>      L1-dcache-loads:u                                                       (0.00%)
     <not counted>      L1-dcache-load-misses:u                                                 (0.00%)
   <not supported>      LLC-loads:u
   <not supported>      LLC-load-misses:u

       0.000741511 seconds time elapsed

       0.000000000 seconds user
       0.000822000 seconds sys



"""

PERF_REPORT_2 = """# started on Sun Jul 23 22:44:31 2023


 Performance counter stats for '/home/vulder/vara-root/benchbuild/results/GenBBBaselineO/SynthSAContextSensitivity-perf_tests@a8c3a8722f,0/SynthSAContextSensitivity/build/bin/ContextSense --compress --mem 10 8':

              1.23 msec task-clock:u                     #    0.000 CPUs utilized
                 0      context-switches:u               #    0.000 /sec
                 0      cpu-migrations:u                 #    0.000 /sec
               132      page-faults:u                    #  107.572 K/sec
           850,975      cycles:u                         #    0.693 GHz                         (12.81%)
           140,154      stalled-cycles-frontend:u        #   16.47% frontend cycles idle
         1,012,322      stalled-cycles-backend:u         #  118.96% backend cycles idle
         1,785,912      instructions:u                   #    2.10  insn per cycle
                                                  #    0.57  stalled cycles per insn
           325,708      branches:u                       #  265.433 M/sec
            11,160      branch-misses:u                  #    3.43% of all branches
           840,918      L1-dcache-loads:u                #  685.298 M/sec                       (87.19%)
     <not counted>      L1-dcache-load-misses:u                                                 (0.00%)
   <not supported>      LLC-loads:u
   <not supported>      LLC-load-misses:u

       5.945920439 seconds time elapsed

       0.000376000 seconds user
       0.001390000 seconds sys



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
        self.assertEqual(self.report_1.elapsed_time, 0.000741511)
        self.assertEqual(self.report_2.elapsed_time, 5.945920439)

    def test_context_switches_parsing(self) -> None:
        """Checks if we correctly parsed the value for context switches."""
        self.assertEqual(self.report_1.ctx_switches, 0)
        self.assertEqual(self.report_2.ctx_switches, 0)

    def test_branch_misses_parsing(self) -> None:
        """Checks if we correctly parsed the value for branch misses."""
        self.assertEqual(self.report_1.branch_misses, 3012)
        self.assertEqual(self.report_2.branch_misses, 11160)

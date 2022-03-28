"""Test AggregatedReport."""
import unittest
from pathlib import Path
import tempfile


from varats.report.gnu_time_report import TimeReportAggregate

GNU_TIME_OUTPUT = """	Command being timed: "sleep 2"
	User time (seconds): 0.00
	System time (seconds): 0.00
	Percent of CPU this job got: 0%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:02.00
	Average shared text size (kbytes): 0
	Average unshared data size (kbytes): 0
	Average stack size (kbytes): 0
	Average total size (kbytes): 0
	Maximum resident set size (kbytes): 2228
	Average resident set size (kbytes): 0
	Major (requiring I/O) page faults: 0
	Minor (reclaiming a frame) page faults: 101
	Voluntary context switches: 3
	Involuntary context switches: 0
	Swaps: 0
	File system inputs: 32
	File system outputs: 0
	Socket messages sent: 0
	Socket messages received: 0
	Signals delivered: 0
	Page size (bytes): 4096
	Exit status: 0
"""


class TestTimeReportAggregate(unittest.TestCase):
    """Test if we can write time reports to `AggregatedReport.tempdir`, zip the contents and read them again afterwards."""

    def test_two_equal_reports(self) -> None:
        """Test if we correctly parse duration event types."""

        num_reports = 2

        with tempfile.TemporaryDirectory() as tmp_dir:

            # Write time reports to `tempdir`.
            tmp_file = Path(tmp_dir) / "TimeAggregateTwoReportsTest.zip"
            time_aggregate = TimeReportAggregate(tmp_file)
            with time_aggregate as time_reports_dir:

                for i in range(num_reports):

                    with open(time_reports_dir / f"time_report_{i}.txt", "w") as time_report_file:

                        time_report_file.write(GNU_TIME_OUTPUT)

            # Read time reports.
            time_aggregate = TimeReportAggregate(tmp_file)
            with time_aggregate:
                self.assertEqual(len(time_aggregate.reports), num_reports)
                self.assertEqual(time_aggregate.wall_clock_time_mean, 2.0)
                self.assertEqual(time_aggregate.wall_clock_time_std, 0)

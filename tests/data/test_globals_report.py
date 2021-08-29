"""Test phasar globals reports."""

import unittest
from pathlib import Path
from unittest import mock

from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)

GLOBALS_REPORT_WITH = """{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 46,
  "#non-top-vals-at-start": 48,
  "#required-globals-generation": 48,
  "auto-globals": true,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 32
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 46,
  "#non-top-vals-at-start": 48,
  "#required-globals-generation": 48,
  "auto-globals": true,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 34
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 46,
  "#non-top-vals-at-start": 48,
  "#required-globals-generation": 48,
  "auto-globals": true,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 33
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 46,
  "#non-top-vals-at-start": 48,
  "#required-globals-generation": 48,
  "auto-globals": true,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 32
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 46,
  "#non-top-vals-at-start": 48,
  "#required-globals-generation": 48,
  "auto-globals": true,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 32
}
----
"""

GLOBALS_REPORT_WITHOUT = """{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 35,
  "#non-top-vals-at-start": 0,
  "#required-globals-generation": 48,
  "auto-globals": false,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 26
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 35,
  "#non-top-vals-at-start": 0,
  "#required-globals-generation": 48,
  "auto-globals": false,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 26
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 35,
  "#non-top-vals-at-start": 0,
  "#required-globals-generation": 48,
  "auto-globals": false,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 26
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 35,
  "#non-top-vals-at-start": 0,
  "#required-globals-generation": 48,
  "auto-globals": false,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 27
}
----
{
  "#analyzed-global-ctors": 0,
  "#analyzed-global-dtors": 0,
  "#global-distinct-types": 130,
  "#global-int-typed": 49,
  "#global-uses": 932,
  "#global-vars": 455,
  "#globals": 455,
  "#non-top-vals-at-end": 35,
  "#non-top-vals-at-start": 0,
  "#required-globals-generation": 48,
  "auto-globals": false,
  "entry-points": "main (or all, if there is no main)",
  "program": "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc",
  "runtime-in-seconds": 26
}
----
"""


class TestGlobalsReport(unittest.TestCase):
    """Test if a blame report is correctly reconstructed from yaml."""

    report_with: GlobalsReportWith
    report_without: GlobalsReportWithout

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=GLOBALS_REPORT_WITH)
        ):
            cls.report_with = GlobalsReportWith(Path('fake_file_path'))

        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=GLOBALS_REPORT_WITHOUT)
        ):
            cls.report_without = GlobalsReportWithout(Path('fake_file_path'))

    def test_num_analyzed_global_ctors(self) -> None:
        self.assertEqual(self.report_with.num_analyzed_global_ctors, 0)
        self.assertEqual(self.report_without.num_analyzed_global_ctors, 0)

    def test_num_analyzed_global_dtors(self) -> None:
        self.assertEqual(self.report_with.num_analyzed_global_dtors, 0)
        self.assertEqual(self.report_without.num_analyzed_global_dtors, 0)

    def test_num_global_distrinct_types(self) -> None:
        self.assertEqual(self.report_with.num_global_distrinct_types, 130)
        self.assertEqual(self.report_without.num_global_distrinct_types, 130)

    def test_num_global_int_typed(self) -> None:
        self.assertEqual(self.report_with.num_global_int_typed, 49)
        self.assertEqual(self.report_without.num_global_int_typed, 49)

    def test_num_global_uses(self) -> None:
        self.assertEqual(self.report_with.num_global_uses, 932)
        self.assertEqual(self.report_without.num_global_uses, 932)

    def test_num_global_vars(self) -> None:
        self.assertEqual(self.report_with.num_global_vars, 455)
        self.assertEqual(self.report_without.num_global_vars, 455)

    def test_num_globals(self) -> None:
        self.assertEqual(self.report_with.num_globals, 455)
        self.assertEqual(self.report_without.num_globals, 455)

    def test_num_non_top_vals_at_end(self) -> None:
        self.assertEqual(self.report_with.num_non_top_vals_at_end, 46)
        self.assertEqual(self.report_without.num_non_top_vals_at_end, 35)

    def test_num_non_top_vals_at_start(self) -> None:
        self.assertEqual(self.report_with.num_non_top_vals_at_start, 48)
        self.assertEqual(self.report_without.num_non_top_vals_at_start, 0)

    def test_num_required_globals_generation(self) -> None:
        self.assertEqual(self.report_with.num_required_globals_generation, 48)
        self.assertEqual(
            self.report_without.num_required_globals_generation, 48
        )

    def test_auto_globals(self) -> None:
        self.assertEqual(self.report_with.auto_globals, True)
        self.assertEqual(self.report_without.auto_globals, False)

    def test_entry_points(self) -> None:
        """Test if we correctly load the entry points."""
        self.assertEqual(
            self.report_with.entry_points, "main (or all, if there is no main)"
        )
        self.assertEqual(
            self.report_without.entry_points,
            "main (or all, if there is no main)"
        )

    def test_program(self) -> None:
        """Test if we correctly load the program name."""
        self.assertEqual(
            self.report_with.program,
            "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc"
        )
        self.assertEqual(
            self.report_without.program,
            "/varats_root/BC_files/xz/xz-xz-e7da44d515-O0_TBAA.bc"
        )

    def test_runs(self) -> None:
        self.assertEqual(self.report_with.runs, 5)
        self.assertEqual(self.report_without.runs, 5)

    def test_runtime_in_secs(self) -> None:
        """Checks if the runtimes are correctly aggregated."""
        self.assertEqual(self.report_with.runtime_in_secs.mean, 32.6)
        self.assertAlmostEqual(
            self.report_with.runtime_in_secs.stddev, 0.8, delta=0.02
        )

        self.assertEqual(self.report_without.runtime_in_secs.mean, 26.2)
        self.assertAlmostEqual(
            self.report_without.runtime_in_secs.stddev, 0.4, delta=0.02
        )

"""Tests that the intrumentation verifier report parses correctly."""
import tempfile
import typing as tp
import unittest
from pathlib import Path

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import ZippedReportFolder

INSTRUMENTATION_VERIFIER_OUTPUTS_SUCCESS: tp.List[str] = [
    """Entered region: 0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000001 ( SrcLoc: ??? [F: main ])

Finalization: Success
---------------------
""",
    """Entered region: 0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000001 ( SrcLoc: ??? [F: main ])
Entered region: 0000000000000000002 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000002 ( SrcLoc: ??? [F: main ])
Entered region: 0000000000000000003 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000003 ( SrcLoc: ??? [F: main ])

Finalization: Success
---------------------
""",
    """Entered region: 0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Entered region: 0000000000000000002 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000002 ( SrcLoc: ??? [F: main ])
Left region:    0000000000000000001 ( SrcLoc: ??? [F: main ])
Entered region: 0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000001 ( SrcLoc: ??? [F: main ])
Entered region: 0000000000000000003 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000003 ( SrcLoc: ??? [F: main ])
Entered region: 0000000000000000004 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    0000000000000000004 ( SrcLoc: ??? [F: main ])

Finalization: Success
---------------------
"""
]

INSTRUMENTATION_VERIFIER_OUTPUTS_FAILURE: tp.List[str] = [
    """Entered region: 1729382256910270467 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    1729382256910270467 ( SrcLoc: ??? [F: main ])

Finalization: Failure
Unclosed Region-ID(s):
  0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
  0000000000000000002 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Wrong Leave-ID(s):
---------------------
""",
    """Entered region: 1729382256910270467 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    1729382256910270467 ( SrcLoc: ??? [F: main ])

Finalization: Failure
Unclosed Region-ID(s):
Wrong Leave-ID(s):
  0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
  0000000000000000002 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
---------------------
""",
    """Entered region: 1729382256910270467 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Left region:    1729382256910270467 ( SrcLoc: ??? [F: main ])

Finalization: Failure
Unclosed Region-ID(s):
  0000000000000000001 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
  0000000000000000002 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
Wrong Leave-ID(s):
  0000000000000000003 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
  0000000000000000004 ( SrcLoc: src/SingleLocalSimple/SLSmain.cpp:14:7 [F: main ])
---------------------
"""
]


class TestInstrumentationVerifierReport(unittest.TestCase):
    """Tests the instrumentation verifier report."""

    def test_success_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = Path(tmp_dir) / "IVR.zip"
            with ZippedReportFolder(tmp_file) as report_folder:
                for i, output in enumerate(
                    INSTRUMENTATION_VERIFIER_OUTPUTS_SUCCESS
                ):
                    with open(
                        Path(report_folder) / f"trace_binary{i}.ivr", "w"
                    ) as bin_file:
                        bin_file.write(output)

            iv_report = InstrVerifierReport(tmp_file)

            self.assertEqual(len(iv_report.binaries()), 3)
            self.assertEqual(iv_report.num_enters_total(), 9)
            self.assertEqual(iv_report.num_leaves_total(), 9)
            self.assertEqual(iv_report.num_unclosed_enters_total(), 0)
            self.assertEqual(iv_report.num_unentered_leaves_total(), 0)
            self.assertDictEqual(
                iv_report.states(), {
                    "binary0": "Success",
                    "binary1": "Success",
                    "binary2": "Success"
                }
            )

            # binary0
            self.assertEqual(iv_report.state("binary0"), "Success")
            self.assertEqual(iv_report.num_enters("binary0"), 1)
            self.assertEqual(iv_report.num_leaves("binary0"), 1)
            self.assertEqual(iv_report.num_unclosed_enters("binary0"), 0)
            self.assertEqual(iv_report.num_unentered_leaves("binary0"), 0)

            # binary1
            self.assertEqual(iv_report.state("binary1"), "Success")
            self.assertEqual(iv_report.num_enters("binary1"), 3)
            self.assertEqual(iv_report.num_leaves("binary1"), 3)
            self.assertEqual(iv_report.num_unclosed_enters("binary1"), 0)
            self.assertEqual(iv_report.num_unentered_leaves("binary1"), 0)

            # binary2
            self.assertEqual(iv_report.state("binary2"), "Success")
            self.assertEqual(iv_report.num_enters("binary2"), 5)
            self.assertEqual(iv_report.num_leaves("binary2"), 5)
            self.assertEqual(iv_report.num_unclosed_enters("binary2"), 0)
            self.assertEqual(iv_report.num_unentered_leaves("binary2"), 0)

    def test_failure_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = Path(tmp_dir) / "IVR.zip"
            with ZippedReportFolder(tmp_file) as report_folder:
                for i, output in enumerate(
                    INSTRUMENTATION_VERIFIER_OUTPUTS_FAILURE
                ):
                    with open(
                        Path(report_folder) / f"trace_binary{i}.ivr", "w"
                    ) as bin_file:
                        bin_file.write(output)

            iv_report = InstrVerifierReport(tmp_file)

            self.assertEqual(len(iv_report.binaries()), 3)
            self.assertEqual(iv_report.num_enters_total(), 3)
            self.assertEqual(iv_report.num_leaves_total(), 3)
            self.assertEqual(iv_report.num_unclosed_enters_total(), 4)
            self.assertEqual(iv_report.num_unentered_leaves_total(), 4)
            self.assertDictEqual(
                iv_report.states(), {
                    "binary0": "Failure",
                    "binary1": "Failure",
                    "binary2": "Failure"
                }
            )

            # binary0
            self.assertEqual(iv_report.state("binary0"), "Failure")
            self.assertEqual(iv_report.num_enters("binary0"), 1)
            self.assertEqual(iv_report.num_leaves("binary0"), 1)
            self.assertEqual(iv_report.num_unclosed_enters("binary0"), 2)
            self.assertEqual(iv_report.num_unentered_leaves("binary0"), 0)

            # binary1
            self.assertEqual(iv_report.state("binary1"), "Failure")
            self.assertEqual(iv_report.num_enters("binary1"), 1)
            self.assertEqual(iv_report.num_leaves("binary1"), 1)
            self.assertEqual(iv_report.num_unclosed_enters("binary1"), 0)
            self.assertEqual(iv_report.num_unentered_leaves("binary1"), 2)

            # binary2
            self.assertEqual(iv_report.state("binary2"), "Failure")
            self.assertEqual(iv_report.num_enters("binary2"), 1)
            self.assertEqual(iv_report.num_leaves("binary2"), 1)
            self.assertEqual(iv_report.num_unclosed_enters("binary2"), 2)
            self.assertEqual(iv_report.num_unentered_leaves("binary2"), 2)


if __name__ == '__main__':
    unittest.main()

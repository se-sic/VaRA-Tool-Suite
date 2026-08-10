import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from tests.helper_utils import TEST_INPUTS_DIR
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_get_test_names,
    ctest_run_testsuite,
    parse_junit_xml,
)


class TestTestsuiteUtils(unittest.TestCase):
    def test_parse_junit_xml(self) -> None:
        test_report_path = TEST_INPUTS_DIR / "result.xml"
        results = parse_junit_xml(test_report_path)

        # Check if the result contains any error or failure
        for test, result in results.items():
            self.assertNotIn(
                result,
                {
                    TestResult.TIMEOUT,
                    TestResult.FAILED,
                    TestResult.UNKNOWN,
                },
            )

    def test_ctest_get_test_names(self) -> None:
        test_project_path = TEST_INPUTS_DIR / "ctest_test_project"

        with TemporaryDirectory() as build_dir, local.cwd(build_dir):
            bb.watch(cmake)("-G", "Unix Makefiles", test_project_path)
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            test_names = list(ctest_get_test_names(Path(build_dir)))

        expected_test_names = ["time", "fail", "timeout"]

        self.assertListEqual(test_names, expected_test_names)

    def test_ctest_run(self) -> None:
        test_project_path = TEST_INPUTS_DIR / "ctest_test_project"

        with TemporaryDirectory() as build_dir, local.cwd(build_dir):
            bb.watch(cmake)("-G", "Unix Makefiles", test_project_path)
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            test_results = ctest_run_testsuite(Path(build_dir))

        self.assertEqual(test_results["(empty).time"], TestResult.PASSED)
        self.assertEqual(test_results["(empty).fail"], TestResult.FAILED)
        # CTest Timeout is just represented as failure in the JUnit XML
        self.assertEqual(test_results["(empty).timeout"], TestResult.FAILED)

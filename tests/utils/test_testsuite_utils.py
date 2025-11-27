import benchbuild as bb

from tests.helper_utils import TEST_INPUTS_DIR
from varats.utils.testsuite_utils import *


def test_parse_junit_xml() -> None:
    test_report_path = TEST_INPUTS_DIR / "result.xml"
    results = parse_junit_xml(test_report_path)

    # Check if the result contains any error or failure
    for test, result in results.items():
        assert not result in {
            TestResult.TIMEOUT, TestResult.FAILED, TestResult.UNKNOWN
        }


def test_ctest_get_test_names() -> None:
    test_report_path = TEST_INPUTS_DIR / "ctest_get_names"
    build_dir = test_report_path / "build"
    test_names = ctest_get_test_names(build_dir)

    expected_test_names = ["time", "fail", "timeout"]

    assert test_names == expected_test_names

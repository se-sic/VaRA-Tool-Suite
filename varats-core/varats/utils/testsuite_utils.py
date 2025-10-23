"""Several utility functions for the testsuite protocol."""
import json
import re
import typing as tp
from enum import Enum
from pathlib import Path

import benchbuild as bb
from junitparser import JUnitXml, junitparser
from plumbum import local, ProcessExecutionError


class TestResult(Enum):
    PASSED = 0,
    FAILED = 1,
    SKIPPED = 2,
    TIMEOUT = 3,
    DISABLED = 4,
    UNKNOWN = 5


def ctest_get_test_names(build_dir: Path) -> tp.Iterable[str]:
    """
    Get the test names for a project using ctest.

    Args:
        build_dir: Path to the build directory to execute ctest in

    Returns:
        A list of test names available in the build directory.
    """
    ctest_cmd = local["ctest"]["--show-only=json-v1"]

    try:
        with local.cwd(build_dir):
            output = ctest_cmd()
    except ProcessExecutionError:
        return []

    test_info = json.loads(output)

    return [test["name"] for test in test_info["tests"]]


def ctest_run_testsuite(
    build_dir: Path,
    test_report_path: tp.Optional[Path] = None,
    tests_to_run: tp.Optional[tp.Iterable[str]] = None,
    tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
) -> tp.Optional[tp.Dict[str, TestResult]]:
    """
    Run a test suite using ctest.

    Args:
        build_dir: Path to the build directory to execute ctest in
        test_report_path: Path to write the test report file to.
        tests_to_run: List of test cases to run. If None, all tests will be run.
        tests_to_exclude: List of test cases to exclude.

    Returns:
        True if all tests passed, False otherwise.
    """
    if tests_to_run is None:
        # In case no test names are given, we run all tests
        tests_to_run = []

    with local.cwd(build_dir):
        ctest_cmd = local["ctest"]
        if test_report_path is None:
            test_report_path = build_dir / "result.xml"
        ctest_cmd = ctest_cmd["--output-junit", test_report_path]

        if tests_to_run:
            test_regex = '|'.join([
                "^" + re.escape(name) for name in tests_to_run
            ])

            if tests_to_exclude:
                exclude_regex = '|'.join([
                    "^" + re.escape(name) for name in tests_to_exclude
                ])
            ctest_cmd = ctest_cmd["-R", test_regex, "-E", exclude_regex]

        ret_code, _, _ = bb.watch(ctest_cmd)()

    results = parse_junit_xml(test_report_path)

    return results


def gtest_get_test_names(build_dir: Path, test_bin: str) -> tp.Iterable[str]:
    """Get the test names
        Returns:
            A list of test names available in the test directory.
    """
    test_path = build_dir / test_bin
    try:
        with local.cwd(build_dir):
            output = local[test_path]["--gtest_list_tests"]
    except ProcessExecutionError:
        return []

    test_names = []

    current_prefix = ""
    for line in output.splitlines():
        if line.endswith("."):
            current_prefix = line
            continue

        test_name = line.split("#", maxsplit=1)[0].strip()

        test_names.append(current_prefix + test_name)

    return test_names


def gtest_run_testsuite(
    build_dir: Path,
    test_bin: Path,
    test_report_path: tp.Optional[Path] = None,
    tests_to_run: tp.Optional[tp.Iterable[str]] = None,
    tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
) -> tp.Optional[tp.Dict[str, TestResult]]:
    """Run the testsuite."""
    if tests_to_exclude is None:
        tests_to_exclude = []
    excluded_tests = ":".join(tests_to_exclude)

    output_file: Path
    if test_report_path:
        output_file = test_report_path.absolute()
    else:
        output_file = build_dir / "results.json"

    gtest_out = "--gtest_output=json:" + output_file.__str__()

    if tests_to_run:
        included_tests = ":".join(tests_to_run)
        with local.cwd(build_dir):
            ret_code, out, err = bb.watch(
                local[test_bin]
                [f"--gtest_filter={included_tests}-{excluded_tests}", gtest_out]
            )()
    else:
        with local.cwd(build_dir):
            # Run all tests except the excluded ones
            ret_code, out, err = bb.watch(
                local[test_bin][f"--gtest_filter=-{excluded_tests}", gtest_out]
            )()

    # if ret_code != 0:  # Should be correct but need to test after this
    #     return False, None

    # TODO: need to figure out how to get all the passed test and fail test
    # look at the json file that is generated
    results = parse_junit_xml(output_file)

    return results


def parse_junit_xml(xml_path: Path) -> tp.Dict[str, TestResult]:
    """Parse the xml test report and return the test results."""
    results: tp.Dict[str, TestResult] = {}
    test_xml = JUnitXml.fromfile(xml_path.absolute().__str__())
    for suite in test_xml:
        suite: junitparser.TestSuite
        suite_name = suite.name if suite.name else "<unknown>"

        for case in suite:
            case: junitparser.TestCase
            case_name = case.name if case.name else "<unknown>"

            if case.is_passed:
                status = TestResult.PASSED
            elif case.is_skipped:
                status = TestResult.SKIPPED
            elif case.is_failure or case.is_error:
                status = TestResult.FAILED
            else:
                status = TestResult.UNKNOWN

            results[f"{suite_name}.{case_name}"] = status

    return results

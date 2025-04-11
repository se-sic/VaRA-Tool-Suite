"""Several utility functions for the testsuite protocol."""
import json
import re
import typing as tp
from pathlib import Path

import benchbuild as bb
from plumbum import local, ProcessExecutionError


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
    tests_to_run: tp.Optional[tp.Iterable[str]] = None
) -> bool:
    """
    Run a test suite using ctest.

    Args:
        build_dir: Path to the build directory to execute ctest in
        test_report_path: Path to write the test report file to.
        tests_to_run: List of test cases to run. If None, all tests will be run.

    Returns:
        True if all tests passed, False otherwise.
    """
    if tests_to_run is None:
        # In case no test names are given, we run all tests
        tests_to_run = []

    with local.cwd(build_dir):
        ctest_cmd = local["ctest"]
        if test_report_path:
            ctest_cmd = ctest_cmd["--output-junit", test_report_path]

        if tests_to_run:
            test_regex = f"^{'|'.join([re.escape(name) for name in tests_to_run])}''$"

            ctest_cmd = ctest_cmd["-R", test_regex]

        ret_code, _, _ = bb.watch(ctest_cmd)()

        return ret_code == 0

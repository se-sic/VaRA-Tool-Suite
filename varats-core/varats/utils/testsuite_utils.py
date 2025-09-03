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
            test_regex = '|'.join([re.escape(name) for name in tests_to_run])
            test_regex = f"^{test_regex}$"

            ctest_cmd = ctest_cmd["-R", test_regex]

        ret_code, _, _ = bb.watch(ctest_cmd)()

        return bool(ret_code == 0)


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
    tests_to_include: tp.Optional[tp.Iterable[str]] = None,
    tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
) -> tp.Tuple[bool, tp.Optional[tp.Dict[str, str]]]:
    """Run the testsuite."""
    included_tests = ":".join(tests_to_include)
    excluded_tests = ":".join(tests_to_exclude)

    gtest_out = ""
    if test_report_path:
        gtest_out = "--gtest_output=json:" + test_report_path.absolute()

    if tests_to_run:
        all_tests = ":".join(tests_to_run)
        with local.cwd(build_dir):
            ret_code, out, err = bb.watch(
                local[test_bin]
                [f"--gtest_filter={all_tests}:{included_tests}-{excluded_tests}",
                 gtest_out]
            )()
    else:
        with local.cwd(build_dir):
            ret_code, out, err = bb.watch(
                local[test_bin][f"--gtest_filter=-{excluded_tests}", gtest_out]
            )()

    if ret_code != 0:  # Should be correct but need to test after this
        return False, None

    # TODO: need to figure out how to get all the passed test and fail test
    passed = failed = 0
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("[  PASSED  ]") and "tests." in line:
            passed = int(line.split()[3])
        elif line.startswith("[  FAILED  ]") and "tests" in line:
            failed = int(line.split()[3])
    if failed > 0:
        return False, None  # Failed some test

    return True, None  # Passed all test

import typing
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple, HTTPUntar
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult


class Cadical(VProject):
    """CaDiCaL SAT solver."""

    NAME = "cadical"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.SOLVER

    SOURCE: typing.ClassVar = [
        PaperConfigSpecificGit(
            project_name="cadical",
            remote="https://github.com/arminbiere/cadical.git",
            local="cadical",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        ),
        PatchVariationSource(),
        HTTPMultiple(
            local="main2024",
            remote={
                "1.0": "https://github.com/se-sic/picoSAT-vara/releases/download/workloads-main-2024-hc/"
            },
            files=[
                "heule-noL-11-12.sanitized.cnf",
                "mp1-ps-5000.cnf",
                "stable-300.cnf",
            ]
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt',
        'install',
        '-y',
        'build-essential',
        'pkg-config',
        'clang',
        'libpcre3',
        'libpcre3-dev',
    )

    WORKLOADS: typing.ClassVar = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("cadical") / RSBinary("cadical"),
                "main2024/heule-noL-11-12.sanitized.cnf",
                label="heule-noL-11-12",
            ),
            VCommand(
                SourceRoot("cadical") / RSBinary("cadical"),
                "main2024/mp1-ps-5000.cnf",
                label="mp1-ps-5000",
            ),
            VCommand(
                SourceRoot("cadical") / RSBinary("cadical"),
                "main2024/stable-300.cnf",
                label="stable-300",
            ),
        ]
    }

    def run_tests(self) -> None: # noqa: D102
        pass

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        """Returns the binaries for a given revision."""
        binary_map = RevisionBinaryMap(get_local_project_repo(Cadical.NAME))

        binary_map.specify_binary(
            "build/cadical", BinaryType.EXECUTABLE, valid_exit_codes=[0, 10, 20]
        )

        return binary_map[revision]

    def compile(self) -> None:
        """Compile the project."""
        src_dir = Path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        make = local["make"]

        with (
            local.cwd(src_dir),
            local.env(CC=str(c_compiler), CXX=str(cxx_compiler)),
        ):
            configure = local["./configure"]
            bb.watch(configure)()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def recompile(self):
        """Recompile the project."""
        src_dir = Path(self.source_of_primary)

        with local.cwd(src_dir):
            make = local["make"]
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    ##############################
    # SupportsTestSuite Protocol #
    ##############################

    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for this project.

        After running this method, the test environment should be prepared such
        that tests are discoverable for the get_test_names() method. This does
        not necessarily mean that the tests are built yet.
        """
        self.compile()

    def build_tests(self) -> None:
        """
        Build the tests for this project.

        Should be called after prepare_test_environment() to build the tests.
        Once this method is called, the tests should be built and ready to run.
        """
        self.recompile()

    def run_testsuite(
        self,
        test_report_path: Path | None = None,
        tests_to_run: tp.Iterable[str] | None = None,
        tests_to_exclude: tp.Iterable[str] | None = None,
    ) -> dict[str, TestResult] | None:
        """
        Run the test suite for this project.

        Args:
            test_report_path: Path to the test report file.
            tests_to_run: List of test cases to run.
                          If None, all tests will be run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            returns a dictionary mapping test names to respective result
            (e.g., 'passed', 'failed', 'skipped').
        """
        __test_suites = {
            "api": self._run_api_tests,
            "usage": self._run_usage_tests,
            "cnf": self._run_cnf_tests,
            "traces": self._run_traces_tests,
            "mbt": self._run_mbt_tests,
        }

        if not tests_to_run:
            tests_to_run = __test_suites.keys()

        if tests_to_exclude:
            tests_to_run = set(tests_to_run) - set(tests_to_exclude)

        test_results = {}
        for suite in tests_to_run:
            if suite not in __test_suites:
                raise ValueError(f"Unknown test suite: {suite}")

            test_results.update(__test_suites[suite]())

        return test_results

    def _run_suite(
        self,
        suite_name: str,
        extract_name: tp.Callable[[str], str | None],
        extract_result: tp.Callable[[str], TestResult | None],
    ) -> dict[str, TestResult]:
        test_results: dict[str, TestResult] = {}

        test_dir = Path(self.source_of_primary) / "test"

        with local.cwd(test_dir):
            test_runner = local[f"./{suite_name}/run.sh"]

            _, stdout, _ = bb.watch(test_runner)()

            output = stdout.strip().splitlines()

            active_test = None
            test_name = ""
            for line in output:
                name = extract_name(line)
                if name:
                    if active_test is not None:
                        # Previous test did not report a result,
                        # mark it as Unknown.
                        test_results[test_name] = TestResult.UNKNOWN
                    active_test = line.split("'")[1]
                    test_name = f"{suite_name}::{active_test}"

                # Lines starting with results:
                # 0 ... <ok|failed>
                result = extract_result(line)
                if result and active_test is not None:
                    if test_name in test_results:
                        test_results[test_name] = max(
                            test_results[test_name], result
                        )
                    else:
                        test_results[test_name] = result
                    active_test = None

        if active_test is not None:
            test_results[f"{suite_name}::{active_test}"] = TestResult.UNKNOWN

        return test_results

    def _run_api_tests(self) -> dict[str, TestResult]:

        def extract_name(line: str) -> str | None:
            if "running API test" in line:
                return line.split("'")[1]
            return None

        def extract_result(line: str) -> TestResult | None:
            if line.startswith("# 0 ... "):
                if "ok" in line:
                    return TestResult.PASSED
                if "failed" in line:
                    return TestResult.FAILED
                return TestResult.UNKNOWN
            return None

        return self._run_suite("api", extract_name, extract_result)

    def _run_usage_tests(self) -> dict[str, TestResult]:

        def extract_name(line: str) -> str | None:
            if "running usage test" in line:
                return line.split("'")[1]
            return None

        def extract_result(line: str) -> TestResult | None:
            if "expected exit code" in line:
                if "ok" in line:
                    return TestResult.PASSED
                if "FAILED" in line:
                    return TestResult.FAILED
                return TestResult.UNKNOWN
            return None

        return self._run_suite("usage", extract_name, extract_result)

    def _run_cnf_tests(self) -> dict[str, TestResult]:

        def extract_name(line: str) -> str | None:
            if "running CNF test" in line:
                return line.split("'")[1]
            return None

        def extract_result(line: str) -> TestResult | None:
            if line.startswith("#"):
                if "ok" in line:
                    return TestResult.PASSED
                if "FAILED" in line:
                    return TestResult.FAILED
                return TestResult.UNKNOWN
            return None

        return self._run_suite("cnf", extract_name, extract_result)

    def _run_traces_tests(self) -> dict[str, TestResult]:

        def extract_name(line: str) -> str | None:
            if "trace/run.sh" in line and "'" in line:
                return line.split("'")[1]
            return None

        def extract_result(line: str) -> TestResult | None:
            if line.startswith("# ... "):
                if "ok" in line:
                    return TestResult.PASSED
                if "failed" in line:
                    return TestResult.FAILED
                return TestResult.UNKNOWN
            return None

        return self._run_suite("trace", extract_name, extract_result)

    def _run_mbt_tests(self) -> dict[str, TestResult]:
        test_dir = Path(self.source_of_primary) / "test"

        with local.cwd(test_dir):
            test_runner = local["./mbt/run.sh"]

            _, stdout, _ = bb.watch(test_runner)()

            output = stdout.strip().splitlines()

            result = TestResult.UNKNOWN

            for line in output:
                if "all tests succeeded" in line:
                    result = TestResult.PASSED
                elif "some tests failed" in line:
                    result = TestResult.FAILED

        return {"mbt": result}

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project.

        Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        test_results = self.run_testsuite()
        if test_results is None:
            return []

        return list(test_results.keys())

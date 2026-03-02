"""DuckDB project module."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError
from scipy.ndimage import label

from varats.experiment.workload_util import WorkloadCategory, RSBinary
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult, parse_junit_xml


class DuckDB(VProject):
    """DuckDB project."""

    NAME = "duckdb"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="duckdb",
            remote="https://github.com/duckdb/duckdb.git",
            local="duckdb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("duckdb") / RSBinary("benchmark_runner"),
                "benchmark/large/ingestion/tpch/native/ingest_lineitem.benchmark",
                label="tpch-csv-ingest-lineitem"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(DuckDB.NAME))

        binary_map.specify_binary("build/release/duckdb", BinaryType.EXECUTABLE)
        binary_map.specify_binary(
            "build/release/benchmark/benchmark_runner", BinaryType.EXECUTABLE
        )
        binary_map.specify_binary(
            "build/release/test/unittest", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def compile(self) -> None:
        version_source = self.source_of(self.primary_source)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source):
            with local.env(
                CC=str(cc_compiler),
                CXX=str(cxx_compiler),
                GEN="ninja",
                BUILD_BENCHMARK="1",
                BUILD_TPCH="1"
            ):
                make = local["make"]

                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self) -> None:
        self.compile()

    def run_tests(self) -> None:
        pass

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
        self.compile()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """
        Run the test suite for this project.

        Args:
            test_report_path: Path to the test report file.
            tests_to_run: List of test cases to run.
                          If None, all tests will be run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            returns a dictionary mapping test names to respective result (e.g., 'passed', 'failed', 'skipped').
        """
        source_dir = local.path(self.source_of_primary)

        with local.cwd(source_dir):
            if not test_report_path:
                test_report_path = Path("test_report.xml")
            test_runner = local["./build/release/test/unittest"][
                "--reporter", "junit", "--out",
                test_report_path.absolute()]

            try:
                bb.watch(test_runner)()
            except ProcessExecutionError as pe:
                print("Error while running tests:")
                print(pe)
                return {}

            # Parse test report
            return parse_junit_xml(test_report_path)

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project in the current
        revision and configuration. Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        source_dir = local.path(self.source_of_primary)

        with local.cwd(source_dir):
            test_runner = local["./build/release/test/unittest"]
            result = test_runner("--list-test-names-only", retcode=None).strip()

        return result.splitlines()

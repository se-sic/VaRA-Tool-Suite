"""DuckDB project module."""
import typing as tp
from collections import defaultdict
from pathlib import Path

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError
from scipy.ndimage import label

from varats.experiment.workload_util import WorkloadCategory, RSBinary, WorkloadSpecificReportAggregate
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    verify_binaries, ProjectBinaryWrapper,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import BaseReport
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult, parse_junit_xml


class DuckDB(VProject):
    """DuckDB project."""

    NAME = "duckdb"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE: tp.ClassVar = [
        PaperConfigSpecificGit(
            project_name="duckdb",
            remote="https://github.com/duckdb/duckdb.git",
            local="duckdb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        PatchVariationSource()
    ]

    WORKLOADS: tp.ClassVar = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("duckdb") / RSBinary("benchmark_runner"),
                "--disable-timeout",
                "benchmark/large/ingestion/tpch/native/ingest_lineitem.benchmark",
                label="tpch-csv-ingest-lineitem"
            ),
            VCommand(
                SourceRoot("duckdb") / RSBinary("benchmark_runner"),
                "--disable-timeout",
                "benchmark/micro/compression/dictionary/dictionary_store_worst_case_with_null.benchmark",
                label="micro-dict-store-wc-null"
            ),
            VCommand(
                SourceRoot("duckdb") / RSBinary("benchmark_runner"),
                "--disable-timeout",
                "benchmark/micro/index/create/create_art_varchar.benchmark",
                label="micro-create-art-varchar"
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> list[ProjectBinaryWrapper]:
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
        self.recompile()

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

class DuckDBBenchmarkRunReport(
    BaseReport,
    shorthand="DDBR",
    file_type=".txt"
):
    """
    Report for run with the DuckDB internal benchmark runner.

    The results are a dictionary mapping benchmark names to the runtime in seconds.
    """

    def __init__(
        self,
        path: Path
    ) -> None:
        super().__init__(path)
        self._results = defaultdict(list)

        with self.path.open() as f:
            # Format of files:
            # name    run    timing
            # <name1> <num1>   <time1>
            # ...
            for line in f:
                if line.startswith("name"):
                    continue
                parts = line.strip().split()
                if len(parts) != 3:
                    continue
                name, _, timing = parts
                self._results[name].append(float(timing))

    @property
    def benchmarks(self) -> str:
        return self._results.keys()

    def measurements(self, benchmark: str) -> list[float]:
        return self._results[benchmark]

class DuckDBBenchmarkAggregate(
    WorkloadSpecificReportAggregate[DuckDBBenchmarkRunReport],
    shorthand="DDBA",
    file_type=".zip"
):
    """
    Aggregate report for multiple runs of the DuckDB internal benchmark runner.

    This simply merges the results of multiple runs into a single report
    """

    def __init__(
        self, path: Path
    ) -> None:
        super().__init__(path, DuckDBBenchmarkRunReport)
        self._results = defaultdict(list)

        for wl in self.workload_names():
            reports = self.reports(wl)

            for report in reports:
                    for benchmark in report.benchmarks:
                        self._results[benchmark].extend(report.measurements(benchmark))

    @property
    def benchmarks(self) -> str:
        return self._results.keys()

    def measurements(self, benchmark: str) -> list[float]:
        return self._results[benchmark]

class DuckDBMPReport(
    MultiPatchReport[DuckDBBenchmarkAggregate],
    shorthand="DDBMP",
    file_type=".zip"
):
    """
    Multi-patch report for the DuckDB internal benchmark runner.

    This aggregates the results of multiple patches into a single report.
    """

    def __init__(
        self, path: Path
    ) -> None:
        super().__init__(path, DuckDBBenchmarkAggregate)

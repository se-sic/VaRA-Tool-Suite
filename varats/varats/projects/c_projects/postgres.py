"""Project file for postgres."""
import shutil
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.experiments.hidden_config.database_utils import (
    SupportsBenchbase,
    BENCHBASE_WORKLOAD_CONFIG_DIR,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    verify_binaries,
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    ProjectBinaryWrapper,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult, parse_junit_xml


def _normalise_test_name(test_name: str) -> str:
    # Test names output by postgres xml are in a weird format.
    # We attempt to fix it to be consistent across runs
    test_name = test_name.strip(" ms")
    test_name = test_name.rsplit(" ", 1)[0]
    return test_name.replace(" ", "")


class PostgreSQL(VProject):
    """PostgreSQL is a powerful, open source object-relational database
    system."""

    NAME = "postgres"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="postgres",
            remote="https://github.com/postgres/postgres.git",
            local="postgres",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        PatchVariationSource()
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(PostgreSQL.NAME))

        binary_map.specify_binary("install/bin/postgres", BinaryType.EXECUTABLE)
        binary_map.specify_binary("install/bin/pgbench", BinaryType.EXECUTABLE)
        binary_map.specify_binary("install/bin/psql", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def compile(self) -> None:
        version_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir = version_source / "build"
        install_dir = version_source / "install"
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        with local.cwd(build_dir):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                configure = local["../configure"]
                make = local["make"]

                bb.watch(configure)(f"--prefix={install_dir}", "--enable-debug")
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
                bb.watch(make)("install")

        with local.cwd(version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        version_source = local.path(self.source_of_primary)
        build_dir = version_source / "build"

        with local.cwd(build_dir):
            make = local["make"]
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            bb.watch(make)("install")

    def run_tests(self) -> None:
        pass

    ###############################
    # SupportsTestSuites protocol #
    ###############################
    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for this project.

        After running this method, the test environment should be prepared such
        that tests are discoverable for the get_test_names() method. This does
        not necessarily mean that the tests are built yet.
        """
        version_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir = version_source / "build-tests"
        install_dir = version_source / "install-tests"
        build_dir.mkdir(parents=True, exist_ok=True)
        install_dir.mkdir(parents=True, exist_ok=True)

        with local.cwd(version_source):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                meson = local["meson"]
                bb.watch(meson)("setup", build_dir)
                with local.cwd(build_dir):
                    bb.watch(meson)(
                        "test", "-q", "--print-errorlogs", "--suite", "setup"
                    )

    def build_tests(self) -> None:
        """
        Build the tests for this project.

        Should be called after prepare_test_environment() to build the tests.
        Once this method is called, the tests should be built and ready to run.
        """
        # No further steps required, as meson setup already configures the tests
        pass

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
        build_dir = local.path(self.source_of_primary) / "build-tests"
        meson = local["meson"]["test", "-q", "--print-errorlogs"]

        if not tests_to_run:
            tests_to_run = self.get_test_names()

        if tests_to_exclude or tests_to_run:
            print(
                "Including and excluding specific tests is currently not supported for PostgreSQL."
            )
            #tests_to_run = [
            #    test for test in tests_to_run if test not in tests_to_exclude
            #]

        with local.cwd(build_dir):
            try:
                bb.watch(meson)("--suite", "regress")
            except ProcessExecutionError as e:
                print(f"Error running tests: {e}")
                return {}

            result_file = Path(build_dir / "meson-logs" / "testlog.junit.xml")

            test_results = {}
            if result_file.exists():
                test_results = parse_junit_xml(result_file)
                test_results = {
                    _normalise_test_name(name): result
                    for name, result in test_results.items()
                }

            if test_report_path:
                shutil.copy(result_file, test_report_path)

            return test_results

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project in the current
        revision and configuration. Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        version_source = local.path(self.source_of_primary)
        build_dir = version_source / "build-tests"

        with local.cwd(build_dir):
            meson_test = local["meson"]["test", "--list"]
            output = bb.watch(meson_test)()[1].strip()
            test_names = output.splitlines()
            return test_names[1:]

    ##############################
    # SupportsBenchbase protocol #
    ##############################

    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""
        return "postgres"

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""
        return "postgres"

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""
        return "jdbc:postgresql://localhost:5432/benchbase"

    def database_binary(
        self, revision: ShortCommitHash
    ) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""
        return [
            b for b in self.binaries_for_revision(revision)
            if b.name == "postgres"
        ][0]

    def start_database_server(self) -> None:
        """Start the database server."""
        # Multiple steps are required:
        # initdb to initialize the database cluster
        # pg_ctl to start the server
        # createdb to create the benchmark database
        # Finally, ./pgctl start to start the server
        install_dir = local.path(self.source_of_primary) / "install"
        initdb = local[install_dir / "bin" / "initdb"]
        pg_ctl = local[install_dir / "bin" / "pg_ctl"]
        createdb = local[install_dir / "bin" / "createdb"]

        # Create a password file for the 'admin' user
        passwd_file = Path(".passwdfile")
        (local["echo"]["password"] > ".pgpass")()
        (local["echo"]["*:*:*:admin:password"] > str(passwd_file.absolute()))()

        passwd_file.chmod(0o600)

        try:
            with local.env(PGPASSFILE=Path(".passwdfile").absolute()):
                bb.watch(initdb)(
                    "-D", "pgdata", "-U", "admin", "-A", "password",
                    "--pwfile=.pgpass"
                )
                bb.watch(pg_ctl)("start", "-D", "pgdata", "-l", "pglog")
                bb.watch(createdb)("-U", "admin", "benchbase")
        except ProcessExecutionError:
            print("Error initializing PostgreSQL database cluster")

    def stop_database_server(self) -> None:
        """Stop the database server."""
        install_dir = local.path(self.source_of_primary) / "install"
        pg_ctl = local[install_dir / "bin" / "pg_ctl"]

        try:
            bb.watch(pg_ctl)("stop", "-D", "pgdata")
        except ProcessExecutionError:
            print("Error stopping PostgreSQL server")

        pg_data_dir = local.path("pgdata")
        shutil.rmtree(pg_data_dir, ignore_errors=True)

        Path(".passwdfile").unlink(missing_ok=True)
        Path(".pgpass").unlink(missing_ok=True)

    def render_workload_config(
        self, workload: str, configuration: tp.Dict[str, tp.Union[bool, str]]
    ) -> Path:
        assert (isinstance(self, SupportsBenchbase))

        return Path(
            BENCHBASE_WORKLOAD_CONFIG_DIR / "postgres" /
            f"sample_{workload}_config.xml"
        )

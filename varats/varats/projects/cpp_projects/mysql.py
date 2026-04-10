import shutil
import subprocess
import typing as tp
import uuid
from pathlib import Path
from time import sleep

import benchbuild as bb
import jinja2
from benchbuild.utils.settings import get_number_of_jobs
from jinja2 import TemplateNotFound, TemplateError
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiments.hidden_config.database_utils import (
    BENCHBASE_EXTRA_FILES_DIR,
    BENCHBASE_WORKLOAD_CONFIG_DIR,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repo,
    RevisionBinaryMap,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.projects.cpp_projects.mariadb import MariaDB
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import TestResult


class MySQL(VProject):
    """MySQL project."""
    NAME = "mysql"
    GROUP = "cpp"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mysql",
            remote="https://github.com/mysql/mysql-server",
            local="mysql",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        PatchVariationSource()
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'build-essential', 'clang', 'cmake',
        'pkg-config', 'bison'
    )

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(*args, **kwargs)
        self.__server_handle: tp.Optional[subprocess.Popen] = None
        self.__log_handle = None

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(MySQL.NAME))

        binary_map.specify_binary("build/bin/mysqld", BinaryType.EXECUTABLE)

        binary_map.specify_binary("build/bin/mysql", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def compile(self) -> None:
        version_source = local.path(self.source_of_primary)

        build_dir = Path(version_source / "build")
        build_dir.mkdir(exist_ok=True)
        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(build_dir):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                cmake = local["cmake"]["-DDOWNLOAD_BOOST=ON",
                                       f"-DWITH_BOOST={build_dir}/boost"]
                make = local["make"]
                bb.watch(cmake)(version_source)
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        build_dir = Path(self.source_of_primary) / "build"

        with local.cwd(build_dir):
            local["make"]("-j", get_number_of_jobs(bb_cfg()))

    def run_tests(self) -> None:
        pass

    ###############################
    # SupportsTestSuites Protocol #
    ###############################
    @property
    def id(self) -> str:
        """We need to override the default id from benchbuild, as it contains
        the @ symbol which causes issues with the test suite of mysql."""
        version_str = str(self.revision)
        return f"{self.name}-{self.group}-{version_str}"

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
        build_dir = Path(self.source_of_primary) / "build"
        test_binary = local[build_dir / "mysql-test" / "mtr"]

        if not test_report_path:
            test_report_path = build_dir / f"test_report-{uuid.uuid4()}.xml"

        with local.cwd(build_dir):
            test_command = test_binary[
                "--mem",
                "--force",
                "--max-test-fail=1000",  # We want to get as many results as possible, so we set a high limit for test failures
                f"--parallel={get_number_of_jobs(bb_cfg())}",
                f"--xml-report={test_report_path.absolute()}"]

            if tests_to_exclude:
                # Build an exclusion regex pattern for the test binary
                # Ensure exact matches
                exclusion_pattern = "|".join([
                    f"^{test}$" for test in tests_to_exclude
                ])

                test_command = test_command[f"--skip-test={exclusion_pattern}"]

            if tests_to_run:
                # Tests that need to be run are simply passed as arguments
                test_command = test_command[*tests_to_run]
            try:
                bb.watch(test_command)(
                    retcode=None
                )  # mtr returns 1 if any test failed, but we want to continue to parse the report
            except Exception as e:
                print(f"Test command failed with error: {e}")
                print(f"Continuing to parse test report at {test_report_path}")

            # Parse test results
            return MariaDB._parse_test_report(test_report_path)

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project in the current
        revision and configuration. Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        build_dir = Path(self.source_of_primary) / "build"
        test_binary = local[build_dir / "mysql-test" / "mtr"]

        with local.cwd(build_dir):
            test_binary = test_binary["--print-testcases"]

            result = test_binary()

            # Test results are printed in the format:
            # <suite_name>.<test_name> '<combinations>'
            # Where the combinations part is optional and may contain multiple combinations separated by commas.
            # If there are no combinations, the test name is just <suite_name>.<test_name>
            # If there are combinations, generate one test name for each combination in the format <suite_name>.<test_name>,<combination>
            test_names = []

            lines = result.splitlines()
            for line in lines:
                # Lines containing test names have the following format:
                # [<test_name>]
                if not line.strip() or not line.startswith("["):
                    continue

                test_name = line.strip().strip("[]")
                test_names.append(test_name)

        return test_names

    ###############################
    # SupportsBenchbase Protocol  #
    ###############################

    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""
        return "mysql"

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""
        return "mysql"

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""
        return "jdbc:mysql://localhost:3306/benchbase?"

    def database_binary(
        self, revision: ShortCommitHash
    ) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""
        for binary in self.binaries_for_revision(revision):
            if binary.name == "mysqld":
                return binary

        raise ValueError(
            f"No server binary found for revision {revision} in MariaDB project."
        )

    def start_database_server(self) -> None:
        """Start the database server."""
        build_dir = Path(self.source_of_primary) / "build"

        data_dir = build_dir / "mysql-data"

        data_dir.mkdir()

        defaults_file = self.__generate_defaults_file(data_dir)

        mysqldbd = local[build_dir / "bin" / "mysqld"]

        with local.cwd(build_dir):
            # First, initialize the database with the defaults file
            bb.watch(
                mysqldbd[f"--defaults-file={defaults_file.absolute()}",
                         "--initialize-insecure"]
            )()

            server_binary = mysqldbd[
                f"--defaults-file={defaults_file.absolute()}"]

            tmp_log_file = build_dir / "mysqld.log"
            self.__log_handle = tmp_log_file.open("w")

            self.__server_handle = server_binary.popen(
                stdout=self.__log_handle, stderr=self.__log_handle
            )

            client_binary = local[build_dir / "bin" / "mysql"][
                f"--defaults-file={defaults_file.absolute()}", "-u", "root"]
            # Wait for the server to start up by trying to connect with the client binary
            sleep(5)

            bb.watch(client_binary
                    )("-e", "CREATE DATABASE IF NOT EXISTS benchbase;")

        # Create benchbase db

    def stop_database_server(self) -> None:
        """Stop the database server."""
        if not self.__server_handle:
            print("No server handle to stop.")
        else:
            self.__server_handle.terminate()
            self.__server_handle.wait(timeout=30)

        if self.__log_handle:
            self.__log_handle.close()

        # Remove auxiliary files created for the server
        build_dir = Path(self.source_of_primary) / "build"
        data_dir = build_dir / "mysql-data"
        defaults_file = self.__defaults_file_path()

        defaults_file.unlink(missing_ok=True)
        shutil.rmtree(data_dir, ignore_errors=True)

    def render_workload_config(
        self, workload: str, configuration: tp.Dict[str, tp.Union[bool, str]]
    ) -> Path:
        """Render the workload configuration for BenchBase."""

        return Path(
            BENCHBASE_WORKLOAD_CONFIG_DIR / "mysql" /
            f"sample_{workload}_config.xml"
        )

    def __defaults_file_path(self) -> Path:
        return Path(self.builddir) / "defaults.cnf"

    def __generate_defaults_file(self, data_dir):
        defaults_file_path = self.__defaults_file_path()

        defaults_file_path.unlink(missing_ok=True)

        # Load the template defaults file and render with jinja2
        template_defaults_file = BENCHBASE_EXTRA_FILES_DIR / "db_config_files" / "mysql.cnf"
        # Render the patch with the arguments
        loader = jinja2.FileSystemLoader(
            searchpath=template_defaults_file.parent
        )
        env = jinja2.Environment(
            loader=loader,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined
        )

        try:
            template = env.get_template(template_defaults_file.name)
        except TemplateNotFound as e:
            raise TemplateError(
                f"Could not find template file '{template_defaults_file}'"
            ) from e

        try:
            render_args = {
                "data_dir": data_dir,
                "socket_path": f"/tmp/{self.run_uuid}-mysql.sock",
            }
            rendered = template.render(render_args)
        except TemplateError:
            # TODO: Discuss what error we want to raise here
            raise

        with defaults_file_path.open("w") as f:
            f.write(rendered)

        return defaults_file_path

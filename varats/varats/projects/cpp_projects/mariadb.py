"""Project file for MariaDB."""
import shutil
import subprocess
import typing as tp
from pathlib import Path
from time import sleep

import benchbuild as bb
import jinja2
from benchbuild.utils.settings import get_number_of_jobs
from jinja2 import TemplateNotFound, TemplateError
from plumbum import local, BG

from varats.experiments.hidden_config.database_utils import (
    SupportsBenchbase,
    BENCHBASE_WORKLOAD_CONFIG_DIR,
    BENCHBASE_EXTRA_FILES_DIR,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    ProjectBinaryWrapper,
    default_cmake_compile,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class MariaDB(VProject):
    """MariaDB is a community-developed, commercially supported fork of the
    MySQL relational database management system (RDBMS), intended to remain free
    and open-source software under the GNU General Public License."""

    NAME = "mariadb"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="mariadb",
            remote="https://github.com/MariaDB/server",
            local="mariadb",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(*args, **kwargs)
        self.__server_handle: tp.Optional[subprocess.Popen] = None

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(MariaDB.NAME))

        # Server binary
        binary_map.specify_binary("build/sql/mariadbd", BinaryType.EXECUTABLE)

        # Client binary
        binary_map.specify_binary("build/client/mariadb", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        default_cmake_compile(self)

    def recompile(self) -> None:
        version_source = self.source_of(self.primary_source)

        with local.cwd(version_source):
            make = local["make"]
            make("-j", get_number_of_jobs(bb_cfg()))

    ##############################
    # SupportsBenchbase protocol #
    ##############################

    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""
        return "mariadb"

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""
        return "mariadb"

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""
        return "jdbc:mariadb://localhost:3306/benchbase"

    def database_binary(
        self, revision: ShortCommitHash
    ) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""

        for binary in self.binaries_for_revision(revision):
            if binary.name == "mariadbd":
                return binary

        raise ValueError(
            f"No server binary found for revision {revision} in MariaDB project."
        )

    def __defaults_file_path(self) -> Path:
        build_dir = Path(self.source_of_primary) / "build"
        return build_dir / "defaults.cnf"

    def __generate_defaults_file(self) -> Path:
        build_dir = Path(self.source_of_primary) / "build"
        defaults_file_path = self.__defaults_file_path()

        defaults_file_path.unlink(missing_ok=True)

        # Load the template defaults file and render with jinja2
        template_defaults_file = BENCHBASE_EXTRA_FILES_DIR / "db_config_files" / "mariadb.cnf"
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
                "socket_path": f"/tmp/{self.run_uuid}-mariadb.sock",
                "data_dir": str(build_dir / "data"),
            }
            rendered = template.render(render_args)
        except TemplateError:
            # TODO: Discuss what error we want to raise here
            raise

        with defaults_file_path.open("w") as f:
            f.write(rendered)

        return defaults_file_path

    def start_database_server(self) -> None:
        """Start the database server."""
        build_dir = Path(self.source_of_primary) / "build"
        defaults_file = self.__generate_defaults_file()

        install_db = local[build_dir / "scripts" / "mariadb-install-db"][
            "--srcdir=..", f"--defaults-file={defaults_file.absolute()}",
            "--auth-root-authentication-method=normal"]
        with local.cwd(build_dir):
            bb.watch(install_db)()

            server_binary = local[
                build_dir / "sql" /
                "mariadbd"][f"--defaults-file={defaults_file.absolute()}"]

            tmp_log_file = build_dir / "mariadb_server.log"
            f = tmp_log_file.open("w")

            self.__server_handle = server_binary.popen(stdout=f, stderr=f)

            client_binary = local[build_dir / "client" / "mariadb"][
                f"--defaults-file={defaults_file.absolute()}", "--user=root"]

            # Copy create script to build directory
            create_script_path = build_dir / "create_benchbase_db.sql"
            shutil.copy(
                BENCHBASE_EXTRA_FILES_DIR / "db_config_files" /
                "mariadb_create.sql", create_script_path
            )

            # Wait for a couple of seconds to ensure the server has started
            sleep(5)
            bb.watch(client_binary)('-e', "source create_benchbase_db.sql;")

    def stop_database_server(self) -> None:
        """Stop the database server."""
        if not self.__server_handle:
            print("No server process to stop.")
        else:
            self.__server_handle.kill()

        # Delete auxiliary files
        build_dir = Path(self.source_of_primary) / "build"
        defaults_file = self.__defaults_file_path()
        defaults_file.unlink(missing_ok=True)
        (build_dir / "mariadb.sock").unlink(missing_ok=True)
        shutil.rmtree(build_dir / "data", ignore_errors=True)

    def render_workload_config(
        self, workload: str, configuration: tp.Dict[str, tp.Union[bool, str]]
    ) -> Path:
        assert (isinstance(self, SupportsBenchbase))

        return Path(
            BENCHBASE_WORKLOAD_CONFIG_DIR / "mariadb" /
            f"sample_{workload}_config.xml"
        )

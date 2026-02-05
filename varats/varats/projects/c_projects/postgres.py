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
from varats.utils.testsuite_utils import TestResult


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
        )
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

                bb.watch(configure)(f"--prefix={install_dir}")
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

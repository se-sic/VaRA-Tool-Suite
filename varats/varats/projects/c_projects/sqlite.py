import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
    ProjectBinaryWrapper,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class SQLite(VProject):
    NAME = "sqlite"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="sqlite",
            remote="https://github.com/sqlite/sqlite",
            local="sqlite",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(get_local_project_repo(SQLite.NAME))

        binary_map.specify_binary("build/sqlite3", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def compile(self) -> None:
        sqlite_source = self.source_of(self.primary_source)
        cc_compiler = bb.compiler.cc(self)
        build_dir = Path(sqlite_source) / "build"
        build_dir.mkdir(exist_ok=True)

        with local.cwd(build_dir), local.env(CC=str(cc_compiler)):
            configure = local["../configure"]
            make = local["make"]

            configure("--enable-all")
            make("sqlite3", "-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(sqlite_source):
            verify_binaries(self)

    def recompile(self) -> None:
        sqlite_source = self.source_of(self.primary_source)

        with local.cwd(sqlite_source / "build"):
            make = local["make"]
            make("sqlite3", "-j", get_number_of_jobs(bb_cfg()))

    def run_tests(self) -> None:
        pass

    # SupportsBenchbase protocol:
    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""
        return "sqlite"

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""
        return self.get_database_name()

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""
        return "jdbc:sqlite:benchbase.db"

    def database_binary(self) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""
        # We do not need a binary to benchmark sqlite with BenchBase, so we create a dummy one.
        dummy_binary = ProjectBinaryWrapper(
            binary_name="sqlite",
            binary_type=BinaryType.EXECUTABLE,
            path_to_binary=Path("/bin/true")
        )

    def start_database_server(self) -> None:
        """Start the database server."""
        # Nothing to do
        return

    def stop_database_server(self) -> None:
        """Stop the database server."""
        # Nothing to do
        return

    def render_workload_config(self, workload: str, configuration):
        ...

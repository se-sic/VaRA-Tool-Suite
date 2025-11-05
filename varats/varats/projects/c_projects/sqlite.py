import typing as tp

import benchbuild as bb
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class SQLite(VProject):
    NAME = "SQLite"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="SQLite",
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

    def compile(self) -> None:
        sqlite_source = self.source_of(self.primary_source)
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(sqlite_source / "build"), local.env(CC=str(cc_compiler)):
            configure = local["../configure"]
            make = local["make"]

            configure("--enable-all")
            make("sqlite3", "-j", get_number_of_jobs(bb_cfg()))

    def recompile(self) -> None:
        sqlite_source = self.source_of(self.primary_source)

        with local.cwd(sqlite_source / "build"):
            make = local["make"]
            make("sqlite3", "-j", get_number_of_jobs(bb_cfg()))

    def run_tests(self) -> None:
        pass

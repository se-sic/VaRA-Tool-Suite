"""Project file for the sqlite project."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class SQLite(VProject):
    """SQLite: lightweight SQL database engine."""

    NAME = "sqlite"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="sqlite",
            remote="https://github.com/sqlite/sqlite.git",
            local="sqlite",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12
                              ).run('apt', 'install', '-y', 'tcl-dev')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(SQLite.NAME))

        binary_map.specify_binary('sqlite3', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        sqlite_version_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(sqlite_version_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./configure"])("--all")
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

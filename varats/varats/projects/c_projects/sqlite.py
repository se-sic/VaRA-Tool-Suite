"""Project file for SQLite."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class SqLite(VProject):
    """SQLite is a C-language library that implements a small, fast, self-
    contained, high-reliability, full-featured, SQL database engine."""

    NAME = 'sqlite'
    GROUP = 'c_projects'
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

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'libtool', 'autoconf')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(SqLite.NAME))

        binary_map.specify_binary('build/sqlite3', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        sqlite_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        build_dir = sqlite_source / "build"
        with local.cwd(build_dir):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["../configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(sqlite_source):
            verify_binaries(self)

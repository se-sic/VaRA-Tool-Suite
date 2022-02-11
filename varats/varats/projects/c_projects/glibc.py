"""Project file for glibc."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Glibc(VProject):
    """Standard GNU C-library."""

    NAME = 'glibc'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.C_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="glibc",
            remote="git://sourceware.org/git/glibc.git",
            local="glibc",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Glibc.NAME))

        binary_map.specify_binary("PLEASE_REPLACE_ME", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        glibc_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        build_dir = glibc_source / "build"
        build_dir.mkdir()
        with local.cwd(build_dir):
            with local.env(CC=str(clang)):
                bb.watch(local["../configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "glibc")]

"""Project file for vim."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Vim(VProject):
    """Text processing tool vim."""

    NAME = 'vim'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.EDITOR

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/vim/vim.git",
            local="vim",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("vim")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("src/vim", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        vim_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(vim_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("vim_development_group", "vim"), ("vim", "vim")]

"""Project file for findutils."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class FindUtils(VProject):
    """Gnu Tools find, xargs, locate."""

    NAME = 'findutils'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="findutils",
            remote="https://github.com/bernhard-voelker/findutils.git",
            local="findutils",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', 'autoconf', 'automake', 'gettext', 'autopoint',
        'pkg-config', 'texinfo'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(FindUtils.NAME)
        )

        binary_map.specify_binary("find", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        make_git_path = get_local_project_git_path(self.NAME)
        clang = bb.compiler.cc(self)
        with local.cwd(make_git_path):
            with local.env(CC=str(clang)):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])()
            bb.watch(make)('-j', get_number_of_jobs(bb_cfg()))
            verify_binaries(self)

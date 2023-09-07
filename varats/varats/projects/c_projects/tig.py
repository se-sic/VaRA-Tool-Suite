"""Project file for tig."""
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
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Tig(VProject):
    """Tig: text-mode interface for Git"""

    NAME = 'tig'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.VERSION_CONTROL

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="tig",
            remote="https://github.com/jonas/tig.git",
            local="tig",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'git', 'libncurses-dev')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Tig.NAME))

        binary_map.specify_binary("src/tig", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        tig_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(tig_version_source):

            with local.env(CC=str(c_compiler)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

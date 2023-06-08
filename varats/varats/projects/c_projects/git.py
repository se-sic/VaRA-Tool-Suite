"""Project file for git."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local
from plumbum.path.utils import delete

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
    get_local_project_git_path,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Git(VProject):
    """Git."""

    NAME = 'git'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.VERSION_CONTROL

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="git",
            remote="https://github.com/git/git.git",
            local="git",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt-get', 'install', '-y', 'libcurl4-openssl-dev', 'zlib1g')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Git.NAME))

        binary_map.specify_binary("git", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        git_source = Path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(git_source):
            with local.env(CC=str(clang)):
                delete("configure", "config.status")
                bb.watch(make)("configure")
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("git", "git")]

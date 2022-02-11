"""Project file for the GNU grep."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import (
    project_filter_generator,
    PaperConfigSpecificGit,
)
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


class Grep(VProject):
    """GNU Grep / UNIX command-line tools (fetched by Git)"""

    NAME = 'grep'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="grep",
            remote="https://github.com/vulder/grep.git",
            local="grep",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/coreutils/gnulib.git",
            local="grep/gnulib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("grep")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'autopoint', 'wget', 'gettext',
        'texinfo', 'rsync', 'automake', 'autotools-dev', 'pkg-config', 'gperf'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Grep.NAME))

        binary_map.specify_binary("src/grep", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        grep_source = local.path(self.source_of_primary)
        with local.cwd(grep_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()), "check")

    def compile(self) -> None:
        grep_source = local.path(self.source_of_primary)
        compiler = bb.compiler.cc(self)
        with local.cwd(grep_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "grep")]

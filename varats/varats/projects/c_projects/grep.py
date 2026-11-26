"""Project file for the GNU grep."""

import sys

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.paper.paper_config import (
    PaperConfigSpecificGit,
    project_filter_generator,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class Grep(VProject):
    """GNU Grep / UNIX command-line tools."""

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
            shallow=False,
            submodule_set_urls={
                "gnulib": "https://github.com/coreutils/gnulib"
            },
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/coreutils/gnulib.git",
            local="grep/gnulib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("grep"),
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
    )

    @override
    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Grep.NAME))

        binary_map.specify_binary("src/grep", BinaryType.EXECUTABLE)

        return binary_map[revision]

    @override
    def run_tests(self) -> None:
        grep_source = local.path(self.source_of_primary)
        with local.cwd(grep_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()), "check")

    @override
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
    def get_cve_product_info(cls) -> list[tuple[str, str]]:
        """Get vendor and product name used to look up CVEs for grep."""
        return [("gnu", "grep")]

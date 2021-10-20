"""Project file for bison."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, git
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
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


class Bison(VProject):
    """
    GNU Bison parser generator.

    (fetched by Git)
    """

    NAME = 'bison'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.PARSER

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/bincrafters/bison.git",
            local="bison",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bison")
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/coreutils/gnulib.git",
            local="bison/gnulib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bison")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autopoint', 'flex',
        'gettext', 'graphviz', 'help2man', 'perl', 'rsync', 'texinfo', 'wget'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([('./src/bison', BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bison_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(bison_source):
            bb.watch(git)("submodule", "update", "--init")

            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

"""Project file for bison."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, git
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
)
from varats.utilss.settings import bb_cfg


class Bison(bb.Project):  # type: ignore
    """
    GNU Bison parser generator.

    (fetched by Git)
    """

    NAME = 'bison'
    GROUP = 'c_projects'
    DOMAIN = 'parser'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/bincrafters/bison.git",
            local="bison",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bison")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([('./src/bison', BinaryType.executable)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bison_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)  # type: ignore
        cxx_compiler = bb.compiler.cxx(self)  # type: ignore
        with local.cwd(bison_source):
            bb.watch(git)("submodule", "update", "--init")  # type: ignore

            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["./bootstrap"])()  # type: ignore
                bb.watch(local["./configure"])()  # type: ignore

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

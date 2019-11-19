"""
Project file for doxygen.
"""
import typing as tp
from pathlib import Path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cxx
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake, cp
from benchbuild.utils.download import with_git

from plumbum.path.utils import delete
from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import wrap_paths_to_binaries, block_revisions, \
    BlockedRevisionRange


@block_revisions([
    # TODO: se-passau/VaRA#536
    BlockedRevisionRange("a6238a4898e20422fe6ef03fce4891c5749b1553",
                         "cf936efb8ae99dd297b6afb9c6a06beb81f5b0fb",
                         "Needs flex <= 2.5.4 and >= 2.5.33")
])
@with_git(
    "https://github.com/doxygen/doxygen.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("doxygen"))
class Doxygen(Project):  # type: ignore
    """ Doxygen """

    NAME = 'doxygen'
    GROUP = 'cpp_projects'
    DOMAIN = 'documentation'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(['doxygen'])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clangxx = cxx(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CXX=str(clangxx)):
                delete("CMakeCache.txt")
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(CFG["jobs"])])

            cp("bin/doxygen", ".")

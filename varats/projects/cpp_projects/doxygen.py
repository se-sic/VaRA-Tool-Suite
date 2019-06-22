from benchbuild.settings import CFG
from benchbuild.utils.compiler import cxx
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake, cp
from benchbuild.utils.download import with_git

from plumbum.path.utils import delete
from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/doxygen/doxygen.git",
    limit=100,
    refspec="HEAD",
    version_filter=project_filter_generator("doxygen"))
class Doxygen(Project):  # type: ignore
    """ Doxygen """

    NAME = 'doxygen'
    GROUP = 'cpp_projects'
    DOMAIN = 'documentation'
    VERSION = 'HEAD'

    BIN_NAMES = ['doxygen']
    SRC_FILE = NAME + "-{0}".format(VERSION)

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

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cxx
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake, cp
from benchbuild.utils.download import with_git

from plumbum.path.utils import delete
from plumbum import local


@with_git("https://github.com/doxygen/doxygen.git", limit=100, refspec="HEAD")
class Doxygen(Project):
    """ Doxygen """

    NAME = 'doxygen'
    GROUP = 'code'
    DOMAIN = 'documentation'
    VERSION = 'HEAD'
    BIN_NAME = NAME

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clangxx = cxx(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CXX=str(clangxx)):
                delete("CMakeCache.txt")
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(CFG["jobs"])])

            cp("bin/doxygen", ".")

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://github.com/marcobambini/gravity.git", limit=100, refspec="HEAD")
class Gravity(Project):
    """ Programming language Gravity """

    NAME = 'gravity'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(CFG["jobs"])])

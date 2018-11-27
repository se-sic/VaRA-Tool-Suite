from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://git.videolan.org/git/x264.git", limit=100, refspec="HEAD")
class X264(prj.Project):
    NAME = 'x264'
    GROUP = 'encoder'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

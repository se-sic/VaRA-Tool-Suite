from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://github.com/tmux/tmux.git", limit=100, refspec="HEAD")
class Tmux(Project):
    """ Terminal multiplexer Tmux """

    NAME = 'tmux'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'
    BIN_NAME = NAME

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./autogen.sh"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

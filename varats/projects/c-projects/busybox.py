from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://github.com/mirror/busybox.git", limit=100, refspec="HEAD")
class busybox(Project):
    """ UNIX utility wrapper Busybox """

    NAME = 'busybox'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)
    clang = ""

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        self.clang = cc(self)
        with local.cwd(self.SRC_FILE):
            run(make["defconfig"])
            run(make["-j", int(CFG["jobs"]), "CC={}".format(str(self.clang))])

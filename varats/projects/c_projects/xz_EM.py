from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make, autoreconf
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://github.com/xz-mirror/xz.git", limit=100, refspec="HEAD")
class Xz_EM(prj.Project):
    NAME = 'xz_EM'
    GROUP = 'encoder'
    DOMAIN = 'version control'
    VERSION = 'HEAD'
    BIN_NAME = 'xz'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(autoreconf["--install"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])


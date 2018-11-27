from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://chromium.googlesource.com/webm/libvpx", limit=100, refspec="HEAD")
class Libvpx(prj.Project):
    NAME = 'libvpx'
    GROUP = 'encoder'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        options = ["--enable-extra-warnings", "--disable-dependency-tracking",
                   "--disable-install-docs", "--disable-docs"]
        configure = local["./configure"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(configure(options))
            run(make["-j", int(CFG["jobs"])])

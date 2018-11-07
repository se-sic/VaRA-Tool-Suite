from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local


@with_git("https://git.savannah.gnu.org/git/gzip.git", limit=100, refspec="HEAD")
class Gzip(prj.Project):
    """ Compression and decompression tool Gzip (fetched by Git) """

    NAME = 'gzip'
    GROUP = 'git'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        self.cflags += ["-Wno-error=string-plus-int",
                        "-Wno-error=shift-negative-value",
                        "-Wno-string-plus-int",
                        "-Wno-shift-negative-value"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./bootstrap"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

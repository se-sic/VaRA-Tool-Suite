"""
Project file for gzip.
"""
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git("https://git.savannah.gnu.org/git/gzip.git",
          limit=200,
          refspec="HEAD",
          shallow_clone=False,
          version_filter=project_filter_generator("gzip"))
class Gzip(prj.Project):  # type: ignore
    """ Compression and decompression tool Gzip (fetched by Git) """

    NAME = 'gzip'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    BIN_NAMES = ['gzip']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += [
            "-Wno-error=string-plus-int", "-Wno-error=shift-negative-value",
            "-Wno-string-plus-int", "-Wno-shift-negative-value"
        ]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./bootstrap",
                          "--gnulib-srcdir=/scratch/breitenj/tmp/gnulib"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

"""
Project file for lrzip.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/ckolivas/lrzip.git",
    limit=200,
    refspec="HEAD",
    version_filter=project_filter_generator("lrzip"))
class Lrzip(Project):  # type: ignore
    """ Compression and decompression tool lrzip (fetched by Git) """

    NAME = 'lrzip'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    BIN_NAMES = ['lrzip']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./autogen.sh"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

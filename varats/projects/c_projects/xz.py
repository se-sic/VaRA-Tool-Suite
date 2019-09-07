"""
Project file for xz.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, autoreconf, cp
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/xz-mirror/xz.git",
    limit=100,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("xz"))
class Xz(Project):  # type: ignore
    """ Compression and decompression tool xz (fetched by Git) """

    NAME = 'xz'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    BIN_NAMES = ['xz']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(autoreconf["--install"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

            # Copy hidden binary file to root for extraction
            cp("src/xz/.libs/xz", ".")

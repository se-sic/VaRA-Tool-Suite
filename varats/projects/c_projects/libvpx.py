"""
Project file for libvpx.
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
    "https://github.com/webmproject/libvpx.git",
    limit=100,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("libvpx"))
class Libvpx(Project):  # type: ignore
    """ Codec SDK libvpx (fetched by Git) """

    NAME = 'libvpx'
    GROUP = 'c_projects'
    DOMAIN = 'codec'
    VERSION = 'HEAD'

    BIN_NAMES = ['vpxdec', 'vpxenc']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

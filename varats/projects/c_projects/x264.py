"""
Project file for x264.
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
    "https://code.videolan.org/videolan/x264.git",
    limit=100,
    refspec="HEAD",
    version_filter=project_filter_generator("x264"))
class X264(Project):
    """ Video encoder x264 (fetched by Git) """

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = 'encoder'
    VERSION = 'HEAD'

    BIN_NAMES = ['x264']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                conf = local["./configure"]
                run(conf["--disable-asm"])
            run(make["-j", int(CFG["jobs"])])

"""
Project file for git.
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
    "git://sourceware.org/git/glibc.git",
    limit=100,
    refspec="HEAD",
    version_filter=project_filter_generator("glibc"))
class Glibc(Project):  # type: ignore
    """ Standard GNU C-library """

    NAME = 'glibc'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    BIN_NAMES = ['fooo']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        local.path(self.SRC_FILE + "/" + "build").mkdir()
        with local.cwd(self.SRC_FILE + "/" + "build"):
            with local.env(CC=str(clang)):
                run(local["./../configure"])
            run(make["-j", int(CFG["jobs"])])

"""
Project file for gravity.
"""
from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.download import with_git

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/marcobambini/gravity.git",
    limit=200,
    refspec="HEAD",
    version_filter=project_filter_generator("gravity"))
class Gravity(Project):  # type: ignore
    """ Programming language Gravity """

    NAME = 'gravity'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    BIN_NAMES = ['gravity']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(CFG["jobs"])])

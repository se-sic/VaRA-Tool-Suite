"""
Project file for gravity.
"""
import typing as tp

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake, git
from benchbuild.utils.download import with_git

from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import get_all_revisions_between
from varats.utils.project_util import BlockedRevisionChecker, \
    BlockedRevisionCheckerDelegate


@with_git(
    "https://github.com/marcobambini/gravity.git",
    limit=200,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("gravity"))
class Gravity(Project, BlockedRevisionChecker):  # type: ignore
    """ Programming language Gravity """

    NAME = 'gravity'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    BIN_NAMES = ['gravity']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    __blocked_revision_checker_delegate = BlockedRevisionCheckerDelegate(NAME)
    __blocked_revision_checker_delegate.block_revisions(
        "0b8e0e047fc3d5e18ead3221ad54920f1ad0eedc",
        "8f417752dd14deea64249b5d32b6138ebc877fa9", "nothing to build")

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        # commit 46133fb47d6da1f0dec27ae23db1d633bc72e9e3 introduced
        # cmake as build system
        with local.cwd(self.SRC_FILE):
            version_id = git("rev-parse", "HEAD").strip()
            cmake_revisions = get_all_revisions_between(
                "46133fb47d6da1f0dec27ae23db1d633bc72e9e3", "master")

        if version_id in cmake_revisions:
            print("CMAKE")
            self.__compile_cmake()
        else:
            print("MAKE")
            self.__compile_make()

    def __compile_cmake(self):
        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(CFG["jobs"])])

    def __compile_make(self):
        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(make["-j", int(CFG["jobs"])])

    @classmethod
    def is_blocked_revision(cls, id: str) -> tp.Tuple[bool, tp.Optional[str]]:
        return cls.__blocked_revision_checker_delegate.is_blocked_revision(id)

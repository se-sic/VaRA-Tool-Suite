"""
Project file for git.
"""
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local
from plumbum.path.utils import delete

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/git/git.git",
    limit=100,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("git"))
class Git(prj.Project):  # type: ignore
    """ Git """

    NAME = 'git'
    GROUP = 'c_projects'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    BIN_NAMES = ['git']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                delete("configure", "config.status")
                run(make["configure"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

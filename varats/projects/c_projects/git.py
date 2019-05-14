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


@with_git("https://github.com/git/git.git", limit=100, refspec="HEAD")
class Git(prj.Project):
    """ Git """

    NAME = 'git'
    GROUP = 'c_projects'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    BIN_NAMES = ['git']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                delete("configure", "config.status")
                run(make["configure"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

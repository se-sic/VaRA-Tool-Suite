from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local

class Tmux(Project):
    """ tmux """

    NAME = 'tmux'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = '2.7'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/tmux/tmux.git"

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir, shallow_clone=False)

    def configure(self):
        clang = cc(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                run(local["./autogen.sh"])
                run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])

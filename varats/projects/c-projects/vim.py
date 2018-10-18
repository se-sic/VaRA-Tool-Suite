from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local
from os import path

class Vim(Project):
    """ Text processing tool vim """

    NAME = 'vim'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = '8.1'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/vim/vim.git"

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir, shallow_clone=False)

    def configure(self):
        clang = cc(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])
        self.src_dir = path.join(self.src_dir, "src")

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local

class busybox(Project):
    """ busybox """

    NAME = 'busybox'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = '1.28.3'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/mirror/busybox.git"
    EnvVars = {}

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir)

    def configure(self):
        clang = cc(self)
        with local.cwd(self.src_dir):
            run(make["defconfig"])

    def build(self):
        with local.cwd(self.src_dir):
            with local.env(**self.EnvVars):
                run(make["-j", CFG["jobs"], "CC=wllvm"])

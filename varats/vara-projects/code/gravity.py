from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local
from os import path

class gravity(Project):
    """ gravity """

    NAME = 'gravity'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = '0.5.1'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/marcobambini/gravity.git"
    EnvVars = {}

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir)

    def configure(self):
        clang = cc(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                with local.env(**self.EnvVars):
                    cmake = local["cmake"]
                    cmake("-G", "Unix Makefiles", ".")

    def build(self):
        with local.cwd(self.src_dir):
            with local.env(**self.EnvVars):
                run(make["-j", CFG["jobs"]])

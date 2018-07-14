from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git
from plumbum import local
from os import path

class glibc(Project):
    """ glibc """

    NAME = 'glibc'
    GROUP = 'code'
    DOMAIN = 'UNIX utils'
    VERSION = '2.27'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "git://sourceware.org/git/glibc.git"
    EnvVars = {}

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir)

    def configure(self):
        clang = cc(self)
        local.path(path.join(self.src_dir, "build")).mkdir()
        with local.cwd(path.join(self.src_dir, "build")):
            with local.env(CC=str(clang)):
                with local.env(**self.EnvVars):
                    run(local["./../configure"])

    def build(self):
        with local.cwd(path.join(self.src_dir, "build")):
            with local.env(**self.EnvVars):
                run(make["-j", CFG["jobs"]])

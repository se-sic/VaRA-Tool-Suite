from benchbuild.settings import CFG
from benchbuild.utils.compiler import cxx
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.downloader import Git

from plumbum.path.utils import delete
from plumbum import local
from os import path

class Doxygen(Project):
    """ Doxygen """

    NAME = 'doxygen'
    GROUP = 'code'
    DOMAIN = 'documentation'
    VERSION = '1.8.14'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/doxygen/doxygen.git"

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir, shallow_clone=False)

    def configure(self):
        clangxx = cxx(self)
        with local.cwd(self.src_dir):
            with local.env(CXX=str(clangxx)):
                delete("CMakeCache.txt")
                cmake("-G", "Unix Makefiles", ".")

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])
        self.src_dir = path.join(self.src_dir, "bin")

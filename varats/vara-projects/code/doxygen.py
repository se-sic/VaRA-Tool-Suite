from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import lt_clang, lt_clang_cxx
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local
from os import path

class Doxygen(prj.Project):
    """ Doxygen """

    NAME = 'doxygen'
    GROUP = 'code'
    DOMAIN = 'documentation'
    VERSION = '1.8.14'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/doxygen/doxygen.git"

    def run_tests(self, experiment, run):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir)

    def configure(self):
        clang = lt_clang(self.cflags, self.ldflags, self.compiler_extension)
        clangxx = lt_clang_cxx(self.cflags, self.ldflags, self.compiler_extension)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang), CXX=str(clangxx)):
                cmake = local["cmake"]
                cmake("-G", "Unix Makefiles", ".")

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])

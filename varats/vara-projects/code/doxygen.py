from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc, cxx
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum.path.utils import delete
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
    EnvVars = {}

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.git_uri, self.src_dir, shallow_clone=False)

    def configure(self):
        clang = cc(self)
        clangxx = cxx(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang), CXX=str(clangxx)):
                with local.env(**self.EnvVars):
                    cmake = local["cmake"]
                    delete("CMakeCache.txt")
                    cmake("-G", "Unix Makefiles", ".")

    def build(self):
        with local.cwd(self.src_dir):
            with local.env(**self.EnvVars):
                run(make["-j", CFG["jobs"]])
        self.src_dir = path.join(self.src_dir, "bin")

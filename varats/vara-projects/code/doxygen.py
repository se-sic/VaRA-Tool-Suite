from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import lt_clang, lt_clang_cxx
from benchbuild.utils.run import run
from benchbuild.utils.wrapping import wrap
import benchbuild.project as prj
from benchbuild.utils.cmd import cp, make, git, pwd, mkdir
from benchbuild.utils.downloader import update_hash, Copy, source_required

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
        tgt_root = CFG["tmp_dir"].value()
        dir = path.join(tgt_root, self.src_dir)
        if not source_required(self.src_dir, tgt_root):
            Copy(dir, ".")
            return

        git("clone", "--depth", "1", self.git_uri, dir)
        update_hash(self.src_dir, tgt_root)
        Copy(dir, ".")

    def configure(self):
        clang = lt_clang(self.cflags, self.ldflags, self.compiler_extension)
        clangxx = lt_clang_cxx(self.cflags, self.ldflags, self.compiler_extension)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang), CXX=str(clangxx)):
                cmake = local["cmake"]
                cmake("-G", "Unix Makefiles", ".")

    def build(self):
        with local.cwd(self.src_dir):
            run(make)

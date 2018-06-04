from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import lt_clang, lt_clang_cxx
from benchbuild.utils.run import run
from benchbuild.utils.wrapping import wrap
import benchbuild.project as prj
from benchbuild.utils.cmd import cp, make, git, pwd
from benchbuild.utils.downloader import update_hash, Copy, source_required

from plumbum import local
from os import path

class Git(prj.Project):
    """ Git """

    NAME = 'git'
    GROUP = 'git'
    DOMAIN = 'version control'
    VERSION = '2.14.3'

    src_dir = NAME + "-{0}".format(VERSION)
    git_uri = "https://github.com/git/git.git"

    def run_tests(self, experiment, run):
        pass

    def download(self):
        tgt_root = CFG["tmp_dir"].value()
        src_dir = path.join(tgt_root, self.src_dir)
        if not source_required(self.src_dir, tgt_root):
            Copy(src_dir, ".")
            return

        git("clone", "--depth", "1", self.git_uri, src_dir)
        update_hash(self.src_dir, tgt_root)
        Copy(src_dir, ".")

    def configure(self):
        clang = lt_clang(self.cflags, self.ldflags, self.compiler_extension)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                run(make["configure"])
                run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])

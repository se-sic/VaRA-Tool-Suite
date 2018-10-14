from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.utils.wrapping import wrap
import benchbuild.project as prj
from benchbuild.utils.cmd import make, git
from benchbuild.utils.downloader import Git
from benchbuild.utils.downloader import update_hash, Copy, source_required

from plumbum.path.utils import delete
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

    def run_tests(self, runner):
        pass

    def download(self):
        tgt_root = str(CFG["tmp_dir"].value())
        dir = path.join(tgt_root, self.src_dir)
        if not source_required(self.src_dir, tgt_root):
            Copy(dir, ".")
            return

        git("clone", self.git_uri, dir)
        update_hash(self.src_dir, tgt_root)
        Copy(dir, ".")
        #Git(self.git_uri, self.src_dir, shallow_clone=false)

    def configure(self):
        clang = cc(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                delete("configure", "config.status")
                run(make["configure"])
                run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])

from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local

class Gzip(prj.Project):
    """gzip aus git"""

    NAME = 'gzip'
    GROUP = 'git'
    DOMAIN = 'version control'
    VERSION = '1.6'

    src_dir = NAME + "-{0}".format(VERSION)
    gzip_uri = "https://git.savannah.gnu.org/git/gzip.git"

    def run_tests(self, runner):
        pass

    def download(self):
        Git(self.gzip_uri, self.src_dir, shallow_clone=False)

    def configure(self):
        self.cflags += ["-Wno-error=string-plus-int",
                        "-Wno-error=shift-negative-value",
                        "-Wno-string-plus-int",
                        "-Wno-shift-negative-value"]

        clang = cc(self)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                run(local["./bootstrap"])
                run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            run(make["-j", CFG["jobs"]])

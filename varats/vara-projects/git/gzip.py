from os import path

from benchbuild.settings import CFG
from benchbuild.utils.compiler import lt_clang, lt_clang_cxx
from benchbuild.utils.run import run
from benchbuild.utils.wrapping import wrap
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.downloader import Git

from plumbum import local

class gzip(prj.Project):
    """gzip aus git"""

    NAME = 'gzip'
    GROUP = 'git'
    DOMAIN = 'version control'
    VERSION = '1.6'

    src_dir = NAME + "-{0}".format(VERSION)
    gzip_uri = "https://github.com/Distrotech/gzip.git"
    EnvVars = {}

    def run_tests(self, experiment, run):
        pass

    def download(self):
        Git(self.gzip_uri, self.src_dir)

    def configure(self):
        self.cflags += ["-Wno-error=string-plus-int",
        "-Wno-error=shift-negative-value", "-Wno-string-plus-int",
        "-Wno-shift-negative-value"]

        clang = lt_clang(self.cflags, self.ldflags, self.compiler_extension)
        with local.cwd(self.src_dir):
            with local.env(CC=str(clang)):
                with local.env(**self.EnvVars):
                    run(local["./configure"])

    def build(self):
        with local.cwd(self.src_dir):
            with local.env(**self.EnvVars):
                run(make["-j", CFG["jobs"]])

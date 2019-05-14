"""
Project file for busybox.
"""
from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/mirror/busybox.git",
    limit=100,
    refspec="HEAD",
    version_filter=project_filter_generator("busybox"))
class busybox(Project):
    """ UNIX utility wrapper Busybox """

    NAME = 'busybox'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    BIN_NAMES = ['fooo']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
        self.download()

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(make["defconfig"])
                run(make["-j", int(CFG["jobs"])])

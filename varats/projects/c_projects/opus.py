"""
Project file for opus.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, cp
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/xiph/opus.git",
    refspec="HEAD",
    version_filter=project_filter_generator("opus"))
class Opus(Project):  # type: ignore
    """
    Opus is a codec for interactive speech and audio transmission
    over the Internet.
    """

    NAME = 'opus'
    GROUP = 'c_projects'
    DOMAIN = 'codec'
    VERSION = 'HEAD'

    BIN_NAMES = ['opus_demo_binary']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./autogen.sh"])
                run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

            cp(".libs/opus_demo", "opus_demo_binary")

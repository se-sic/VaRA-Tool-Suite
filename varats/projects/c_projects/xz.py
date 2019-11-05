"""
Project file for xz.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, autoreconf, cp, git
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local
from varats.utils.project_util import get_all_revisions_between

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://github.com/xz-mirror/xz.git",
    limit=200,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("xz"))
class Xz(Project):  # type: ignore
    """ Compression and decompression tool xz (fetched by Git) """

    NAME = 'xz'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    BIN_NAMES = ['xz']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        # commit 46133fb47d6da1f0dec27ae23db1d633bc72e9e3 introduced
        # cmake as build system
        with local.cwd(self.SRC_FILE):
            version_id = git("rev-parse", "HEAD").strip()
            cmake_revisions = get_all_revisions_between(
                "5d018dc03549c1ee4958364712fb0c94e1bf2741", "fda4724d8114fccfa31c1839c15479f350c2fb4c")

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(autoreconf["--install"])

                if version_id in cmake_revisions:
                    run(local["./configure"]["--enable-dynamic=yes"])
                else:
                    run(local["./configure"])
            run(make["-j", int(CFG["jobs"])])

            # Copy hidden binary file to root for extraction
            cp("src/xz/.libs/xz", ".")

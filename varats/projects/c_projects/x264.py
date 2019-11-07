"""
Project file for x264.
"""
from benchbuild.project import Project
from benchbuild.settings import CFG
from benchbuild.utils.cmd import make, git
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local
from varats.utils.project_util import get_all_revisions_between

from varats.paper.paper_config import project_filter_generator


@with_git(
    "https://code.videolan.org/videolan/x264.git",
    limit=200,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("x264"))
class X264(Project):  # type: ignore
    """ Video encoder x264 (fetched by Git) """

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = 'encoder'
    VERSION = 'HEAD'

    BIN_NAMES = ['x264']
    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        with local.cwd(self.SRC_FILE):
            version_id = git("rev-parse", "HEAD").strip()
            old_revisions = get_all_revisions_between(
                "5dc0aae2f900064d1f58579929a2285ab289a436",
                "290de9638e5364c37316010ac648a6c959f6dd26")

        if version_id in old_revisions:
            self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                conf = local["./configure"]
                run(conf["--disable-asm"])
            run(make["-j", int(CFG["jobs"])])

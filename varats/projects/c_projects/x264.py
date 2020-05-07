"""Project file for x264."""
import typing as tp
from pathlib import Path

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import git, make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (
    get_all_revisions_between,
    wrap_paths_to_binaries,
)


@with_git(
    "https://code.videolan.org/videolan/x264.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("x264")
)
class X264(Project):  # type: ignore
    """Video encoder x264 (fetched by Git)"""

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = 'encoder'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(["x264"])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        with local.cwd(self.SRC_FILE):
            version_id = git("rev-parse", "HEAD").strip()
            old_revisions = get_all_revisions_between(
                "5dc0aae2f900064d1f58579929a2285ab289a436",
                "290de9638e5364c37316010ac648a6c959f6dd26"
            )

        if version_id in old_revisions:
            self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                conf = local["./configure"]
                run(conf["--disable-asm"])
            run(make["-j", int(BB_CFG["jobs"])])

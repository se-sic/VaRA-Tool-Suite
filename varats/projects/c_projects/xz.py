"""
Project file for xz.
"""
import typing as tp
from pathlib import Path

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import make, autoreconf, git
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run

from plumbum import local
from varats.utils.project_util import (get_all_revisions_between,
                                       block_revisions, BugAndFixPair)

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import wrap_paths_to_binaries


@block_revisions([
    BugAndFixPair("cf49f42a6bd40143f54a6b10d6e605599e958c0b",
                  "4c7ad179c78f97f68ad548cb40a9dfa6871655ae",
                  "missing file api/lzma/easy.h"),
    BugAndFixPair("335fe260a81f61ec99ff5940df733b4c50aedb7c",
                  "24e0406c0fb7494d2037dec033686faf1bf67068",
                  "use of undeclared LZMA_THREADS_MAX"),
])
@with_git("https://github.com/xz-mirror/xz.git",
          refspec="HEAD",
          shallow_clone=False,
          version_filter=project_filter_generator("xz"))
class Xz(Project):  # type: ignore
    """ Compression and decompression tool xz (fetched by Git) """

    NAME = 'xz'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(['src/xz/.libs/xz'])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        # dynamic linking is off by default until
        # commit f9907503f882a745dce9d84c2968f6c175ba966a
        # (fda4724 is its parent)
        with local.cwd(self.SRC_FILE):
            version_id = git("rev-parse", "HEAD").strip()
            revisions_wo_dynamic_linking = get_all_revisions_between(
                "5d018dc03549c1ee4958364712fb0c94e1bf2741",
                "fda4724d8114fccfa31c1839c15479f350c2fb4c")

        self.cflags += ["-fPIC"]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(autoreconf["--install"])

                if version_id in revisions_wo_dynamic_linking:
                    run(local["./configure"]["--enable-dynamic=yes"])
                else:
                    run(local["./configure"])
            run(make["-j", int(BB_CFG["jobs"])])

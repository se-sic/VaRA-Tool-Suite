"""Project file for doxygen."""
import typing as tp
from pathlib import Path

from benchbuild.project import Project
from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import cmake, cp, make
from benchbuild.utils.compiler import cxx
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from plumbum import local
from plumbum.path.utils import delete

from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (
    BugAndFixPair,
    block_revisions,
    wrap_paths_to_binaries,
)


@block_revisions([
    # TODO: se-passau/VaRA#536
    BugAndFixPair(
        "a6238a4898e20422fe6ef03fce4891c5749b1553",
        "cf936efb8ae99dd297b6afb9c6a06beb81f5b0fb",
        "Needs flex <= 2.5.4 and >= 2.5.33"
    ),
    BugAndFixPair(
        "093381b3fc6cc1e97f0e737feca04ebd0cfe538d",
        "cf936efb8ae99dd297b6afb9c6a06beb81f5b0fb",
        "Needs flex <= 2.5.4 and >= 2.5.33"
    )
])
@with_git(
    "https://github.com/doxygen/doxygen.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("doxygen")
)
class Doxygen(Project):  # type: ignore
    """Doxygen."""

    NAME = 'doxygen'
    GROUP = 'cpp_projects'
    DOMAIN = 'documentation'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(['doxygen'])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clangxx = cxx(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CXX=str(clangxx)):
                delete("CMakeCache.txt")
                cmake("-G", "Unix Makefiles", ".")
            run(make["-j", int(BB_CFG["jobs"])])

            cp("bin/doxygen", ".")

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("doxygen", "doxygen")]

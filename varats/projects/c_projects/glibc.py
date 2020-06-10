"""Project file for glibc."""
import typing as tp

from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.settings import bb_cfg
from varats.utils.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
)


@with_git(
    "git://sourceware.org/git/glibc.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("glibc")
)
class Glibc(Project, CVEProviderHook):  # type: ignore
    """Standard GNU C-library."""

    NAME = 'glibc'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(["PLEASE_REPLACE_ME"])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        clang = cc(self)
        local.path(self.SRC_FILE + "/" + "build").mkdir()
        with local.cwd(self.SRC_FILE + "/" + "build"):
            with local.env(CC=str(clang)):
                run(local["./../configure"])
            run(make["-j", get_number_of_jobs(bb_cfg())])

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "glibc")]

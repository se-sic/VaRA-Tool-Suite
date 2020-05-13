"""
Project file for busybox.
"""
import typing as tp

from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (wrap_paths_to_binaries,
                                       ProjectBinaryWrapper)


@with_git("https://github.com/mirror/busybox.git",
          refspec="HEAD",
          shallow_clone=False,
          version_filter=project_filter_generator("busybox"))
class Busybox(Project, CVEProviderHook):  # type: ignore
    """UNIX utility wrapper BusyBox"""

    NAME = 'busybox'
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
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(make["defconfig"])
                run(make["-j", int(BB_CFG["jobs"])])

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("busybox", "busybox")]

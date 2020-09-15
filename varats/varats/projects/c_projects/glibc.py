"""Project file for glibc."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.provider.cve.cve_provider import CVEProviderHook
from varats.utilss.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
)
from varats.utilss.settings import bb_cfg


class Glibc(bb.Project, CVEProviderHook):  # type: ignore
    """Standard GNU C-library."""

    NAME = 'glibc'
    GROUP = 'c_projects'
    DOMAIN = 'UNIX utils'

    SOURCE = [
        bb.source.Git(
            remote="git://sourceware.org/git/glibc.git",
            local="glibc",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("glibc")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            ("PLEASE_REPLACE_ME", BinaryType.executable)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        glibc_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)  # type: ignore
        build_dir = glibc_source / "build"
        build_dir.mkdir()
        with local.cwd(build_dir):
            with local.env(CC=str(clang)):
                bb.watch(local["../configure"])()  # type: ignore
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gnu", "glibc")]

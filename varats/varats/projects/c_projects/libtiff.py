"""Project file for libtiff."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
)
from varats.utils.settings import bb_cfg


class Libtiff(bb.Project, CVEProviderHook):  # type: ignore
    """Libtiff is a library for reading and writing Tagged Image File Format
    files."""

    NAME = 'libtiff'
    GROUP = 'c_projects'
    DOMAIN = 'Image File Format'

    SOURCE = [
        bb.source.Git(
            remote="https://gitlab.com/libtiff/libtiff.git",
            local="libtiff",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libtiff")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(["libtiff/.libs/libtiff.so"])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libtiff_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        with local.cwd(libtiff_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(local["./autogen.sh"])()
                configure = bb.watch(local["./configure"])
                configure()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Libtiff", "Libtiff")]

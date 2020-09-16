"""Project file for poppler."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
)
from varats.provider.cve.cve_provider import CVEProviderHook
from varats.utils.settings import bb_cfg


class Poppler(bb.Project, CVEProviderHook):  # type: ignore
    """Poppler is a free software utility library for rendering Portable
    Document Format documents."""

    NAME = 'poppler'
    GROUP = 'cpp_projects'
    DOMAIN = 'pdf library'

    SOURCE = [
        bb.source.Git(
            remote="https://gitlab.freedesktop.org/poppler/poppler.git",
            local="poppler",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("poppler")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([("libpoppler.so", BinaryType.executable)]
                                     )

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        poppler_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)  # type: ignore
        cxx_compiler = bb.compiler.cxx(self)  # type: ignore
        with local.cwd(poppler_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")  # type: ignore
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Poppler", "Poppler")]

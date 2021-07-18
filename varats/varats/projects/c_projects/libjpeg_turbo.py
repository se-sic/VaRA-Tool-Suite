"""Project file for libjpeg-turbo."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
    verify_binaries,
)
from varats.utils.settings import bb_cfg


class LibjpegTurbo(bb.Project):  # type: ignore
    """libjpeg-turbo is a JPEG image codec."""

    NAME = 'libjpeg_turbo'
    GROUP = 'c_projects'
    DOMAIN = 'JPEG image codec'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/libjpeg-turbo/libjpeg-turbo",
            local="libjpeg-turbo",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libjpeg_turbo")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            ("libjpeg.so", BinaryType.SHARED_LIBRARY)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libjpeg_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)  # type: ignore
        with local.cwd(libjpeg_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")  # type: ignore
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("JpegCodec", "Libjpeg")]

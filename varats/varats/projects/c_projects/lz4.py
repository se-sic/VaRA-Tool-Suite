"""Project file for lz4."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Lz4(VProject):
    """
    LZ4 is lossless compression algorithm.

    (fetched by Git)
    """

    NAME = 'lz4'
    GROUP = 'c_projects'
    DOMAIN = 'compression'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/lz4/lz4.git",
            local="lz4",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("lz4")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([('lz4', BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        lz4_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(lz4_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Yann Collet", "LZ4")]

"""Project file for libvpx."""
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


class Libvpx(VProject):
    """Codec SDK libvpx (fetched by Git)"""

    NAME = 'libvpx'
    GROUP = 'c_projects'
    DOMAIN = 'codec'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/webmproject/libvpx.git",
            local="libvpx",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libvpx")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'yasm')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("vpxdec", BinaryType.EXECUTABLE),
                                       ("vpxenc", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libvpx_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(libvpx_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("john_koleszar", "libvpx")]

"""Project file for zeromq."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Libzmq(VProject):
    """The ZeroMQ lightweight messaging kernel is a library which extends the
    standard socket interfaces with features traditionally provided by
    specialised messaging middleware products."""

    NAME = 'libzmq'
    GROUP = 'cpp_projects'
    DOMAIN = 'messaging'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/zeromq/libzmq.git",
            local="libzmq_git",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libzmq")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'cmake', 'build-essential', 'gnutls-dev',
        'libsodium-dev', 'pkg-config'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ("build/lib/libzmq.so", BinaryType.SHARED_LIBRARY)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libzmq_version_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        mkdir(libzmq_version_source / "build")
        with local.cwd(libzmq_version_source / "build"):
            with local.env(CXX=str(cpp_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(libzmq_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Zeromq", "Libzmq")]

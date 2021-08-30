"""Project file for libsigrok."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
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


class Libsigrok(VProject):
    """
    The sigrok project aims at creating a portable, cross-platform,
    Free/Libre/Open-Source signal analysis software suite.

    (fetched by Git)
    """

    NAME = 'libsigrok'
    GROUP = 'c_projects'
    DOMAIN = 'signal processing'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/sigrokproject/libsigrok.git",
            local="libsigrok",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("libsigrok")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autotools-dev',
        'libtool', 'pkg-config', 'libzip-dev', 'libglib2.0-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ('.libs/libsigrok.so', BinaryType.SHARED_LIBRARY)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        sigrok_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        with local.cwd(sigrok_source):
            with local.env(CC=str(cc_compiler)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

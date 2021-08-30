"""Project file for openvpn."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, autoreconf
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


class OpenVPN(VProject):
    """
    OpenVPN is open-source commercial software that implements virtual private
    network techniques to create secure point-to-point or site-to-site
    connections in routed or bridged configurations and remote access
    facilities.

    (fetched by Git)
    """

    NAME = 'openvpn'
    GROUP = 'c_projects'
    DOMAIN = 'VPN'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/openvpn/openvpn.git",
            local="openvpn",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("openvpn")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'libssl-dev', 'openssl', 'autoconf', 'automake',
        'libtool', 'liblz4-dev', 'liblzo2-dev', 'libpam0g-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ('./src/openvpn/openvpn', BinaryType.EXECUTABLE)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        openvpn_source = local.path(self.source_of(self.primary_source))

        self.cflags += ["-fPIC"]

        c_compiler = bb.compiler.cc(self)
        with local.cwd(openvpn_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(autoreconf)("-vi")
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Openvpn", "Openvpn")]

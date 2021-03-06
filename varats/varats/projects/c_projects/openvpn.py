"""Project file for openvpn."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, autoreconf
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
)
from varats.provider.cve.cve_provider import CVEProviderHook
from varats.utils.settings import bb_cfg


class OpenVPN(bb.Project, CVEProviderHook):  # type: ignore
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

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([
            ('./src/openvpn/openvpn', BinaryType.executable)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        openvpn_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        with local.cwd(openvpn_source):
            with local.env(CC=str(compiler)):
                bb.watch(autoreconf)("-vi")
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Openvpn", "Openvpn")]

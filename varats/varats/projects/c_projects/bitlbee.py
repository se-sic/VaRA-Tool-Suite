"""Project file for bitlbee."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    wrap_paths_to_binaries,
    ProjectBinaryWrapper,
    BinaryType,
)
from varats.provider.cve.cve_provider import CVEProviderHook
from varats.utilss.settings import bb_cfg


class Bitlbee(bb.Project, CVEProviderHook):  # type: ignore
    """
    BitlBee brings IM (instant messaging) to IRC clients.

    (fetched by Git)
    """

    NAME = 'bitlbee'
    GROUP = 'c_projects'
    DOMAIN = 'chat'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/bitlbee/bitlbee.git",
            local="bitlbee",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("bitlbee")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries([('bitlbee', BinaryType.executable)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bitlbee_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)  # type: ignore
        with local.cwd(bitlbee_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./configure"])()  # type: ignore

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Bitlbee", "Bitlbee"), ("Bitlbee", "Bitlbee-libpurple")]

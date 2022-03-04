"""Project file for bitlbee."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Bitlbee(VProject):
    """
    BitlBee brings IM (instant messaging) to IRC clients.

    (fetched by Git)
    """

    NAME = 'bitlbee'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CHAT_CLIENT

    SOURCE = [
        PaperConfigSpecificGit(
            "bitlbee",
            remote="https://github.com/bitlbee/bitlbee.git",
            local="bitlbee",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Bitlbee.NAME))

        binary_map.specify_binary('bitlbee', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bitlbee_source = local.path(self.source_of(self.primary_source))

        compiler = bb.compiler.cc(self)
        with local.cwd(bitlbee_source):
            with local.env(CC=str(compiler)):
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Bitlbee", "Bitlbee"), ("Bitlbee", "Bitlbee-libpurple")]

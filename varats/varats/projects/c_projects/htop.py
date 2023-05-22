"""Project file for htop."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    verify_binaries,
    get_local_project_git_path,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    typed_revision_range,
)
from varats.utils.settings import bb_cfg


class Htop(VProject):
    """Process visualization tool (fetched by Git)"""

    NAME = 'htop'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="htop",
            remote="https://github.com/htop-dev/htop.git",
            local="htop",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'autotools-dev',
        'libtool'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Htop.NAME))

        binary_map.specify_binary('htop', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        htop_source = local.path(self.source_of_primary)
        htop_version_source = Path(self.source_of_primary)
        htop_version = ShortCommitHash(self.version_of_primary)

        configure_flags: tp.List[str] = []

        # older htop versions do not declare some globals as extern properly
        old_revs = GoodBadSubgraph(["d6231bab89d634da5564491196b7c478db038505"],
                                   ["dfd9279f87791e36a5212726781c31fbe7110361"],
                                   "Needs CFLAGS=-fcommon")
        if htop_version in typed_revision_range(
            old_revs, htop_version_source, ShortCommitHash
        ):
            configure_flags += ["CFLAGS=-fcommon"]

        clang = bb.compiler.cc(self)
        with local.cwd(htop_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])(*configure_flags)

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Htop", "Htop")]

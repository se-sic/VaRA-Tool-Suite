"""Project file for libmpack."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, SingleRevision
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Libmpack(VProject):
    """Library providing a simple implementation of msgpack in C."""

    NAME = 'libmpack'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.FILE_FORMAT

    SOURCE = [
        block_revisions([
            SingleRevision("c1f28db8df877a036fefc848b8fdbe0923f72c11"),
            SingleRevision("9028f80482b7da61a065d2688f130c0add9d4262"),
        ])(
            PaperConfigSpecificGit(
                project_name="libmpack",
                remote="https://github.com/libmpack/libmpack.git",
                local="libmpack",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    @staticmethod
    def binaries_for_revision(
            revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        """Returns a list of binaries for the given revision."""
        binary_map = RevisionBinaryMap(get_local_project_repo(Libmpack.NAME))

        binary_map.specify_binary('build/debug/libmpack.la', BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        """Runs tests for libmpack. Currently none."""
        pass

    def compile(self) -> None:
        """Compile the project."""
        libmpack_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(libmpack_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(make)('-j', get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        """Returns CVE product information."""
        return [("libmpack", "libmpack")]

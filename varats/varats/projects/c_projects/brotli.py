"""Project file for brotli."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import mkdir, make
from benchbuild.utils.revision_ranges import RevisionRange, block_revisions
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg


class Brotli(VProject):
    """Brotli compression format."""

    NAME = 'brotli'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        block_revisions([
            RevisionRange(
                '8f30907d0f2ef354c2b31bdee340c2b11dda0fb0',
                '378485b097fd7b80a5e404a3cb912f7b18f78cdb',
                "building not unified"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="brotli",
                remote="https://github.com/google/brotli.git",
                local="brotli_git",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'cmake')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Brotli.NAME))

        binary_map.specify_binary(
            "out/brotli",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "5814438791fb2d4394b46e5682a96b68cd092803", "HEAD"
            )
        )
        binary_map.specify_binary(
            "bin/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
                "5814438791fb2d4394b46e5682a96b68cd092803"
            )
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        brotli_version_source = local.path(self.source_of_primary)
        brotli_git_path = get_local_project_git_path(self.NAME)
        brotli_version = ShortCommitHash(self.version_of_primary)
        with local.cwd(brotli_git_path):
            configure_revisions = get_all_revisions_between(
                "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
                "5814438791fb2d4394b46e5682a96b68cd092803", ShortCommitHash
            )
        c_compiler = bb.compiler.cc(self)
        if brotli_version in configure_revisions:
            with local.cwd(brotli_version_source):
                with local.env(CC=str(c_compiler)):
                    bb.watch(local["./configure"])()
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        else:
            mkdir(brotli_version_source / "out")
            with local.cwd(brotli_version_source / "out"):
                with local.env(CC=str(c_compiler)):
                    bb.watch(local["../configure-cmake"])()
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(brotli_version_source):
            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("google", "brotli")]

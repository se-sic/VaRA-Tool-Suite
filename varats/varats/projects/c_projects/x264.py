"""Project file for x264."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    get_all_revisions_between,
    RevisionBinaryMap,
)
from varats.utils.settings import bb_cfg


class X264(VProject):
    """Video encoder x264 (fetched by Git)"""

    NAME = 'x264'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["5dc0aae2f900064d1f58579929a2285ab289a436"],
                            ["6490f4398d9e28e65d7517849e729e14eede8c5b"],
                            "Does not build on x64 out of the box")
        ])(
            PaperConfigSpecificGit(
                project_name="x264",
                remote="https://code.videolan.org/videolan/x264.git",
                local="x264",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(X264.NAME))

        binary_map.specify_binary("x264", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        x264_version_source = local.path(self.source_of_primary)
        x264_version = ShortCommitHash(self.version_of_primary)

        fpic_revisions = get_all_revisions_between(
            "5dc0aae2f900064d1f58579929a2285ab289a436",
            "290de9638e5364c37316010ac648a6c959f6dd26", ShortCommitHash,
            x264_version_source
        )
        ldflags_revisions = get_all_revisions_between(
            "6490f4398d9e28e65d7517849e729e14eede8c5b",
            "275ef5332dffec445a0c5a78dbc00c3e0766011d", ShortCommitHash,
            x264_version_source
        )

        if x264_version in fpic_revisions:
            self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(x264_version_source):
            with local.env(CC=str(clang)):
                configure_flags = ["--disable-asm"]
                if x264_version in ldflags_revisions:
                    configure_flags.append("--extra-ldflags=\"-static\"")
                bb.watch(local["./configure"])(configure_flags)
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

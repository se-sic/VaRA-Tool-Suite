"""Project file for x264."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.revision_ranges import block_revisions, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg


class X265(VProject):
    """Video encoder x265 (fetched by Git)"""

    NAME = 'x265'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="x265",
            remote="https://bitbucket.org/multicoreware/x265_git.git",
            local="x265",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(X265.NAME))

        binary_map.specify_binary("x265", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        x265_version_source = local.path(self.source_of_primary)

        cc = bb.compiler.cc(self)
        cxx = bb.compiler.cxx(self)

        with local.cwd(x265_version_source / "build"):
            with local.env(CC=str(cc), CXX=str(cxx)):
                bb.watch(local["cmake"])("-G", "Unix Makefiles", "../source")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        x265_version_source = local.path(self.source_of_primary)

        with local.cwd(x265_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

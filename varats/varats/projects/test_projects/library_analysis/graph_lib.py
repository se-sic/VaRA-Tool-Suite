"""Project implementation for the GraphLib library analysis repository."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import (
    VaraTestRepoSource,
    VaraTestRepoSubmodule,
)
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class GraphLib(VProject):
    """Graph library demo project with library upgrade scenarios."""

    NAME = 'GraphLib'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="GraphLib",
            remote="LibraryAnalysisRepos/GraphLib/GraphDemo",
            local="GraphLib/GraphDemo",
            refspec="HEAD",
            limit=None,
            shallow=False
        ),
        VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos/GraphLib/libgraph",
            local="GraphLib/libgraph",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("GraphLib")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(GraphLib.NAME)
        )

        binary_map.specify_binary("build/src/demo", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)

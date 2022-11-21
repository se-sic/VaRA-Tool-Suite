"""Projects to show case multi author coordination scenarios."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, mkdir, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    verify_binaries,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class MultiAuthorCoordination(VProject):
    """Example project demonstrating a scenario where multiple authors interact
    with each other through file, function and data-flows."""

    NAME = 'MutliMethodAuthorCoordination'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="MutliMethodAuthorCoordination",
            remote="BlameAnalysisRepos/MutliMethodAuthorCoordination",
            local="MutliMethodAuthorCoordinatio",
            refspec="HEAD",
            limit=None
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([
            ("build/computeService", BinaryType.EXECUTABLE)
        ])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        mkdir("-p", source / "build")

        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "../")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(source):
            verify_binaries(self)

"""Example project for feature analyses."""
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from plumbum import local

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    verify_binaries,
    BinaryType,
    get_local_project_git_path,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


class FeatureTestRepo(VProject):
    """Example project for feature analyses."""

    NAME = 'FeatureInteractionRepo'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="FeatureInteractionRepo",
            remote="FeatureAnalysisRepos/FeatureInteractionExample",
            local="FeatureInteractionRepo",
            refspec="HEAD",
            limit=None
        ),
        FeatureSource(),
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("FeatureInteractionRepo") / RSBinary("main"),
                label="main-no-input"
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(FeatureTestRepo.NAME)
        ).specify_binary("main", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        self.cflags += ["-fno-exceptions"]

        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(source):
            bb.watch(cxx_compiler)("main.cpp", "-o", "main")

            verify_binaries(self)


class CommitFeatureInteractionExample(VProject):
    """Example project for commit feature interactions."""

    NAME = 'CommitFeatureInteractionExample'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="CommitFeatureInteractionExample",
            remote="FeatureAnalysisRepos/CommitFeatureInteractionExample",
            local="CommitFeatureInteractionExample",
            refspec="HEAD",
            limit=None
        ),
        FeatureSource(),
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(CommitFeatureInteractionExample.NAME)
        ).specify_binary("main", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        self.cflags += ["-fno-exceptions"]

        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(source):
            bb.watch(cxx_compiler)("main.cpp", "-o", "main")

            verify_binaries(self)

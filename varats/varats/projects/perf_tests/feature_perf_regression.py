"""Project file for the feature performance case study collection."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
    get_tagged_commits,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import (
    RevisionBinaryMap,
    ShortCommitHash,
    FullCommitHash,
)
from varats.utils.settings import bb_cfg


class FeaturePerfRegression(VProject, ReleaseProviderHook):
    """Test project for identifying performance regressions across revisions."""

    NAME = 'FeaturePerfRegression'
    GROUP = 'perf_tests'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="FeaturePerfRegression",
            remote="https://github.com/se-sic/FeaturePerfRegression.git",
            local="FeaturePerfRegression",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("FeaturePerfRegression") /
                RSBinary("CompressionTool"),
                label="FeaturePerfRegression-no-input"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(FeaturePerfRegression.NAME)
        )
        binary_map.specify_binary(
            'build/bin/CompressionTool', BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        feature_perf_regression_source = local.path(
            self.source_of(self.primary_source)
        )

        # Disable exceptions
        self.cflags += ["-fno-exceptions"]

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", feature_perf_regression_source / "build")

        with local.cwd(feature_perf_regression_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(feature_perf_regression_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        release_regex = "^v[0-9]+$"

        tagged_commits = get_tagged_commits(cls.NAME)
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(release_regex, tag)]

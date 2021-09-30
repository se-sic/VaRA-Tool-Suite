"""Projects in vara-test-repos used for testing the bug provider."""
import typing as tp

import benchbuild as bb
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    VaraTestRepoSource,
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash


class BasicBugDetectionTestRepo(VProject):
    """Example project demonstrating how to use a repo from the vara-test-
    repos."""

    NAME = 'basic_bug_detection_test_repo'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            remote="BugDetectionRepos/BasicTestRepo",
            local="basic_test_repo",
            refspec="HEAD",
            limit=None,
            version_filter=project_filter_generator("basic_test_repo")
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(source):
            bb.watch(c_compiler)("main.c", "-o", "main")

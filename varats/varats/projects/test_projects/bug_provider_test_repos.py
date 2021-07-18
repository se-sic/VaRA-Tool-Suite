"""Projects in vara-test-repos used for testing the bug provider."""
import typing as tp

import benchbuild as bb
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    VaraTestRepoSource,
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
)


class BasicBugDetectionTestRepo(bb.Project):  # type: ignore
    """Example project demonstrating how to use a repo from the vara-test-
    repos."""

    NAME = 'basic_bug_detection_test_repo'
    DOMAIN = 'testing'
    GROUP = 'test_projects'

    SOURCE = [
        VaraTestRepoSource(
            remote="BugDetectionRepos/BasicTestRepo",
            local="basic_test_repo",
            refspec="HEAD",
            limit=None,
            version_filter=project_filter_generator("basic_test_repo")
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(source):
            bb.watch(c_compiler)("main.c", "-o", "main")

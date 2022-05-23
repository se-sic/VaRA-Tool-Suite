"""Example project demonstrating how to use a repo from the vara-test-repos."""
import typing as tp

import benchbuild as bb
from plumbum import local

from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash


class ExampleTestRepo(VProject):
    """Example project demonstrating how to use a repo from the vara-test-
    repos."""

    NAME = 'example_test_repo'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="example_test_repo",
            remote="BasicTestRepos/ExampleRepo",
            local="example_repo",
            refspec="origin/HEAD",
            limit=None
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

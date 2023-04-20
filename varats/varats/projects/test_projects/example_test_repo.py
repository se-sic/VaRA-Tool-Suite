"""Example project demonstrating how to use a repo from the vara-test-repos."""
import typing as tp

import benchbuild as bb
from plumbum import local

from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


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
            refspec="HEAD",
            limit=None
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(ExampleTestRepo.NAME)
        ).specify_binary("main", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(source):
            bb.watch(c_compiler)("main.c", "-o", "main")

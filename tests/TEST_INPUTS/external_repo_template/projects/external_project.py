"""Dummy external project for registry tests."""
import typing as tp

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash


class ExternalProject(VProject):
    """Dummy external project for registry tests only."""

    NAME = 'external_project'
    DOMAIN = ProjectDomains.TEST
    GROUP = 'external_repo_template'

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='external_project',
            remote="https://github.com/xz-mirror/xz.git",
            local="external_project",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return []

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        pass

"""Project file for Dune"""
import typing as tp

from plumbum import local

from benchbuild.utils import cmd
import benchbuild as bb

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash


class Dune(VProject):
    """Simulation framework for various applications in mathematics and physics"""

    NAME = 'Dune'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='Dune',
            remote='git@github.com:se-sic/dune-VaRA.git',
            local='dune-VaRA',
            refspec='origin/HEAD',
            limit=None,
            shallow=False
        )
    ]

    # TODO: Container support

    @staticmethod
    def binaries_for_revision(revision: ShortCommitHash) -> tp.List['ProjectBinaryWrapper']:
        pass

    def compile(self) -> None:
        """Compile the project using the in-built tooling from dune"""
        version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(version_source):
            dunecontrol = cmd['./dune-common/bin/dunecontrol']

            bb.watch(dunecontrol)('--module=dune-performance-regressions', 'all')

    def run_tests(self) -> None:
        pass

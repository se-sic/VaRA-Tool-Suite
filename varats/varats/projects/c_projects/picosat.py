"""Project file for PicoSAT."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, Command, SourceRoot
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    get_tagged_commits,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
)
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


class PicoSAT(VProject, ReleaseProviderHook):
    """HYPRE is a library of high performance preconditioners and solvers
    featuring multigrid methods for the solution of large, sparse linear systems
    of equations on massively parallel computers."""

    NAME = 'picosat'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="picosat",
            remote="https://github.com/bnico99/picoSAT-mirror",
            local="picosat",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("picosat") / RSBinary("picosat"),
                "-s",
                "42",
                label="workload1",
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(PicoSAT.NAME))
        binary_map.specify_binary('picosat', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        picosat_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(picosat_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["./configure"])(["--trace", "--stats"])
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(picosat_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        release_regex = "^picosat-[0-9]+$"

        tagged_commits = get_tagged_commits(cls.NAME)
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(release_regex, tag)]

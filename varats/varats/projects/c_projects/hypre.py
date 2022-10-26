"""Project file for Hypre."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake
from benchbuild.utils.revision_ranges import block_revisions, SingleRevision
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
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


class Hypre(VProject, ReleaseProviderHook):
    """HYPRE is a library of high performance preconditioners and solvers
    featuring multigrid methods for the solution of large, sparse linear systems
    of equations on massively parallel computers."""

    NAME = 'hypre'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        block_revisions([
            SingleRevision(
                "7c5ce339f18c19965edea47d40c572c2bf8b3aea",
                "Undeclared identifier 'HYPRE_BRANCH_NAME'"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="hypre",
                remote="https://github.com/hypre-space/hypre.git",
                local="hypre",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Hypre.NAME))
        binary_map.specify_binary('src/cmbuild/test/ij', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        hypre_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(hypre_source / "src" / "cmbuild"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)(
                    "-DHYPRE_WITH_MPI=OFF", "-DHYPRE_BUILD_TESTS=ON", ".."
                )

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(hypre_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        major_release_regex = "^(v|V)[0-9]+(\\.|-)[0-9]+(\\.|-)0[a-z]?$"
        minor_release_regex = "^(v|V)[0-9]+(\\.|-)[0-9]+(\\.|-)[1-9]+[a-z]?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.MAJOR:
            return [(FullCommitHash(h), tag)
                    for h, tag in tagged_commits
                    if re.match(major_release_regex, tag)]
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)]

"""Project file for Hypre."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import ReleaseProviderHook
from varats.utils.git_util import RevisionBinaryMap, ShortCommitHash
from varats.utils.settings import bb_cfg


class Hypre(VProject, ReleaseProviderHook):
    """
    HYPRE is a library of high performance preconditioners and solvers featuring
    multigrid methods for the solution of large, sparse linear systems of
    equations on massively parallel computers.

    (fetched by Git)
    """

    NAME = 'hypre'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="hypre",
            remote="https://github.com/hypre-space/hypre.git",
            local="hypre",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
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

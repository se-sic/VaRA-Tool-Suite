"""Project file for Z3."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, mkdir
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


class Z3(VProject, ReleaseProviderHook):
    """
    Z3 is a theorem prover from Microsoft Research.

    (fetched by Git)
    """

    NAME = 'z3'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="z3",
            remote="https://github.com/Z3Prover/z3.git",
            local="z3",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Z3.NAME))
        binary_map.specify_binary('build/z3', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        z3_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", z3_source / "build")

        with local.cwd(z3_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "../")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(z3_source):
            verify_binaries(self)

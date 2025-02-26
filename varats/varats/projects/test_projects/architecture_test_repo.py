"""Project file for lepton."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


class Architecture_Test(VProject):
    """Lepton is a tool and file format for losslessly compressing JPEGs by an
    average of 22%."""

    NAME = 'architecture_test'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="architecture_test",
            remote="https://github.com/Sinerum/feature-architecture-test",
            local="feature-architecture-test",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource()
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Architecture_Test.NAME)
        )

        binary_map.specify_binary(
            "Example/build/Example", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        local_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        c_compiler = bb.compiler.cc(self)
        mkdir("-p", local_source / "Example/build")
        with local.cwd(local_source / "Example/build"):
            with local.env(CC=str(c_compiler), CXX=str(cpp_compiler)):
                bb.watch(cmake)("..")

            bb.watch(make)("-j8")

        with local.cwd(local_source):
            verify_binaries(self)

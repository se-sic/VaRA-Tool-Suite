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
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


class Lepton(VProject):
    """Lepton is a tool and file format for losslessly compressing JPEGs by an
    average of 22%."""

    NAME = 'lepton'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="lepton",
            remote="https://github.com/dropbox/lepton",
            local="lepton",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'git', 'cmake', 'make')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Lepton.NAME))

        binary_map.specify_binary("build/lepton", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        lepton_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        mkdir("-p", lepton_source / "build")
        with local.cwd(lepton_source / "build"):
            with local.env(CXX=str(cpp_compiler)):
                bb.watch(cmake)("..")

            bb.watch(make)("-j8")

        with local.cwd(lepton_source):
            verify_binaries(self)

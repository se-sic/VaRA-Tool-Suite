"""Project file for ECT."""
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


class Ect(VProject):
    """
    Efficient Compression Tool (or ECT) is a C++ file optimizer.

    It supports PNG, JPEG, GZIP and ZIP files.
    """

    NAME = 'ect'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="ect",
            remote="https://github.com/fhanau/Efficient-Compression-Tool.git",
            local="ect",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'nasm', 'git', 'cmake', 'make')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Ect.NAME))

        binary_map.specify_binary("build/ect", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        ect_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        mkdir(ect_source / "build")
        with local.cwd(ect_source / "build"):
            with local.env(CXX=str(cpp_compiler)):
                bb.watch(cmake)("../src")

            bb.watch(make)()

        with local.cwd(ect_source):
            verify_binaries(self)

"""Project file for capstone."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash


class Capstone(VProject):
    """Capstone is a disassembly framework with the target of becoming the
    ultimate disasm engine for binary analysis and reversing in the security
    community."""

    NAME = 'capstone'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.BINARY_ANALYSIS_FRAMEWORK

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='capstone',
            remote="https://github.com/capstone-engine/capstone.git",
            local="capstone",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'cmake')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Capstone.NAME))

        binary_map.specify_binary('build/cstool', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        capstone_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(capstone_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):

                cmake_args = [
                    "-B",
                    "build",
                    "-DCMAKE_BUILD_TYPE=Release",
                ]

                bb.watch(cmake)(*cmake_args)

            bb.watch(cmake)("--build", "build")

            verify_binaries(self)

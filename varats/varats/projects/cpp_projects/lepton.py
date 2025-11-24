"""Project file for lepton."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import WorkloadCategory, RSBinary
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


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

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("lepton") / RSBinary("lepton"),
                "-benchmark",
                label="lepton-benchmark"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Lepton.NAME))

        binary_map.specify_binary("build/lepton", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        lepton_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        c_compiler = bb.compiler.cc(self)
        mkdir("-p", lepton_source / "build")
        with local.cwd(lepton_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cpp_compiler)):
                bb.watch(cmake)("..")

            bb.watch(make)("-j8")

        with local.cwd(lepton_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        lepton_source = local.path(self.source_of_primary)

        with local.cwd(lepton_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

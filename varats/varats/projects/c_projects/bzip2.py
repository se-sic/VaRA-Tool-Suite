"""Project file for xz."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import mkdir, cmake
from benchbuild.source import HTTP
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from benchbuild.command import Command, SourceRoot, WorkloadSet


class Bzip2(VProject):
    """Compression and decompression tool bzip2 (fetched by Git)"""

    NAME = 'bzip2'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="bzip2",
            remote="https://github.com/libarchive/bzip2.git",
            local="bzip2",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        HTTP(
            local="countries-land-1km.geo.json",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0/countries-land-1km.geo.json"
            }
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                "--compress",
                "--best",
                "--verbose",
                "--keep",
                "--force",
                "countries-land-1km.geo.json",
                label="BZ2-Countries"
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Bzip2.NAME))

        binary_map.specify_binary('build/bzip2', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bzip2_source = local.path(self.source_of(self.primary_source))

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", bzip2_source / "build")

        with local.cwd(bzip2_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("..")

            bb.watch(cmake)(
                "--build", ".", "--config", "Release", "-j",
                get_number_of_jobs(bb_cfg())
            )

        with local.cwd(bzip2_source):
            verify_binaries(self)

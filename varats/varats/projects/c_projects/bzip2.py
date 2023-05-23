"""Project file for xz."""
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import mkdir, cmake
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import RSBinary, WorkloadCategory
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
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0"
            },
            files=[
                "countries-land-1m.geo.json", "countries-land-10m.geo.json",
                "countries-land-100m.geo.json"
            ]
        )
    ]
    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            Command(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                "--compress",
                "--best",
                "-vvv",
                "--keep",
                # bzip2 compresses very fast even on the best setting, so we
                # need the three input files to get approximately 30 seconds
                # total execution time
                "geo-maps/countries-land-1m.geo.json",
                "geo-maps/countries-land-10m.geo.json",
                "geo-maps/countries-land-100m.geo.json",
                creates=[
                    "geo-maps/countries-land-1m.geo.json.bz2",
                    "geo-maps/countries-land-10m.geo.json.bz2",
                    "geo-maps/countries-land-100m.geo.json.bz2"
                ]
            )
        ],
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

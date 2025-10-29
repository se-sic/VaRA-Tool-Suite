"""Project file for 7zip."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class SevenZip(VProject):
    """Compression and decompression tool SevenZip (fetched by Git)"""

    NAME = '7zip'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="7zip",
            remote="https://github.com/mcmilk/7-Zip.git",
            local="7zip",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
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
        ),
        # TODO: Compressed Data for decompression workload ?
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("7zip") / RSBinary("7zz"),
                ConfigParams(),
                "geo-maps/countries-land-100m.geo.json.7z",
                "--",
                "geo-maps/countries-land-100m.geo.json",
                label="countries-100m-geo",
                creates=[
                    "geo-maps/countries-land-100m.geo.json.7z",
                ],
                requires_all_args={"a"}
            ),
            # TODO: Decompression workload ?
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("7zip") / RSBinary("7zz"),
                ConfigParams(),
                "geo-maps/countries-land-10m.geo.json.7z",
                "--",
                "geo-maps/countries-land-10m.geo.json",
                label="countries-10m-geo",
                creates=[
                    "geo-maps/countries-land-10m.geo.json.7z",
                ],
                requires_all_args={"a"}
            ),
            #TODO: Decompression workload ?
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("7zip") / RSBinary("7zz"),
                ConfigParams(),
                "geo-maps/countries-land-1m.geo.json.7z",
                "--",
                "geo-maps/countries-land-1m.geo.json",
                label="countries-1m-geo",
                creates=[
                    "geo-maps/countries-land-1m.geo.json.7z",
                ],
                requires_all_args={"a"}
            ),
            # TODO: Decompression workload ?
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(SevenZip.NAME))

        binary_map.specify_binary(
            'CPP/7zip/Bundles/Alone2/b/c/7zz',
            BinaryType.EXECUTABLE,
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        zip7_source = Path(self.source_of_primary)
        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        make = local["make"]

        with local.cwd(zip7_source / "CPP" / "7zip" / "Bundles" / "Alone2"):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(make)(
                    "-f", "../../cmpl_clang.mak", "-j",
                    get_number_of_jobs(bb_cfg())
                )

        with local.cwd(zip7_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        self.compile()

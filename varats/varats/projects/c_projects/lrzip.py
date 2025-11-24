"""Project file for lrzip."""
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.source import HTTP, HTTPMultiple
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
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


class Lrzip(VProject):
    """Compression and decompression tool lrzip (fetched by Git)"""

    NAME = 'lrzip'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="lrzip",
            remote="https://github.com/ckolivas/lrzip.git",
            local="lrzip",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        # TODO: auto unzipper for BB?
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
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'tar', 'libz-dev', 'autoconf', 'libbz2-dev',
        'liblzo2-dev', 'liblz4-dev', 'coreutils', 'libtool'
    )

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "geo-maps/countries-land-1km.geo.json",
                label="countries-land-1km",
                creates=["countries-land-1km.geo.json.lrz"]
            ),
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "geo-maps/countries-land-100m.geo.json",
                label="countries-land-100m",
                creates=["countries-land-100m.geo.json.lrz"]
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "geo-maps/countries-land-10m.geo.json",
                label="countries-land-10m",
                creates=["countries-land-10m.geo.json.lrz"]
            ),
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("lrzip") / RSBinary("lrzip"),
                ConfigParams(),
                "geo-maps/countries-land-1m.geo.json",
                label="countries-land-1m",
                creates=["countries-land-1m.geo.json.lrz"]
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Lrzip.NAME))

        binary_map.specify_binary("lrzip", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        lrzip_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        with local.cwd(lrzip_source):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self):
        lrzip_source = local.path(self.source_of_primary)

        with local.cwd(lrzip_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("lrzip_project", "lrzip")]

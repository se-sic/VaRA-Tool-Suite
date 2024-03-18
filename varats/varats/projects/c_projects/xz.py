"""Project file for xz."""
import typing as tp

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import autoreconf, make
from benchbuild.utils.revision_ranges import (
    block_revisions,
    GoodBadSubgraph,
    RevisionRange,
)
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    get_all_revisions_between,
    RevisionBinaryMap,
)
from varats.utils.settings import bb_cfg


class Xz(VProject):
    """Compression and decompression tool xz (fetched by Git)"""

    NAME = 'xz'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        block_revisions([
            GoodBadSubgraph(["cf49f42a6bd40143f54a6b10d6e605599e958c0b"],
                            ["4c7ad179c78f97f68ad548cb40a9dfa6871655ae"],
                            "missing file api/lzma/easy.h"),
            GoodBadSubgraph(["335fe260a81f61ec99ff5940df733b4c50aedb7c"],
                            ["24e0406c0fb7494d2037dec033686faf1bf67068"],
                            "use of undeclared LZMA_THREADS_MAX"),
            RevisionRange(
                "5d018dc03549c1ee4958364712fb0c94e1bf2741",
                "c324325f9f13cdeb92153c5d00962341ba070ca2",
                "Initial git import without xz"
            )
        ])(
            PaperConfigSpecificGit(
                project_name='xz',
                remote="https://github.com/xz-mirror/xz.git",
                local="xz",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
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
                "countries-land-1km.geo.json", "countries-land-250m.geo.json"
            ]
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_11).run(
        'apt', 'install', '-y', 'autoconf', 'autopoint', 'automake',
        'autotools-dev', 'libtool', 'pkg-config'
    )

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "-k",
                # Use output_param to ensure input file
                # gets appended after all arguments.
                output_param=["{output}"],
                output=SourceRoot("geo-maps/countries-land-250m.geo.json"),
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.xz"]
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "-k",
                "-9e",
                "--compress",
                "--threads=1",
                "--format=xz",
                "-vv",
                # Use output_param to ensure input file
                # gets appended after all arguments.
                output_param=["{output}"],
                output=SourceRoot("geo-maps/countries-land-250m.geo.json"),
                label="countries-land-250m",
                creates=["geo-maps/countries-land-250m.geo.json.xz"],
                requires_all_args={"--compress"},
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Xz.NAME))

        binary_map.specify_binary(
            'src/xz/xz',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("5d018dc035", "3f86532407")
        )

        binary_map.specify_binary(
            'src/xz/.libs/xz',
            BinaryType.EXECUTABLE,
            override_entry_point='src/xz/xz',
            only_valid_in=RevisionRange("880c330938", "master")
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        xz_git_path = get_local_project_git_path(self.NAME)
        xz_version_source = local.path(self.source_of_primary)
        xz_version = self.version_of_primary

        # dynamic linking is off by default until
        # commit f9907503f882a745dce9d84c2968f6c175ba966a
        # (fda4724 is its parent)
        with local.cwd(xz_git_path):
            revisions_wo_dynamic_linking = get_all_revisions_between(
                "5d018dc03549c1ee4958364712fb0c94e1bf2741",
                "fda4724d8114fccfa31c1839c15479f350c2fb4c", ShortCommitHash
            )

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(xz_version_source):
            with local.env(CC=str(clang)):
                bb.watch(autoreconf)("--install")
                configure = bb.watch(local["./configure"])

                if xz_version in revisions_wo_dynamic_linking:
                    configure("--enable-dynamic=yes")
                else:
                    configure()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("tukaani", "xz")]

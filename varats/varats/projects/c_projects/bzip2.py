"""Project file for xz."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple, HTTPUntar
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.revision_ranges import RevisionRange, GoodBadSubgraph
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
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    ShortCommitHash,
    RevisionBinaryMap,
    typed_revision_range,
)
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
        ),
        FeatureSource(),
        HTTPMultiple(
            local="geo-maps-compr",
            remote={
                "1.0":
                    "https://github.com/se-sic/compression-data/"
                    "raw/master/bzip2/geo-maps/"
            },
            files=[
                "countries-land-100m.geo.json.bz2",
                "countries-land-10m.geo.json.bz2",
                "countries-land-1m.geo.json.bz2"
            ]
        ),
        HTTPUntar(
            local="cantrbry.tar.gz",
            remote={
                "1.0":
                    "http://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
            }
        )
    ]
    _AUTOTOOLS_VERSIONS = GoodBadSubgraph([
        "8cfd87aed5ba8843af50569fb440489b1ca74259"
    ], ["e264a7f7c44fae62f5be9840946f6bc0e8cd6512"],
                                          "Uses autotools instead of cmake")
    _MAKE_VERSIONS = GoodBadSubgraph([
        "33d134030248633ffa7d60c0a35a783c46da034b"
    ], ["8cfd87aed5ba8843af50569fb440489b1ca74259"], "Uses a basic Makefile")

    CONTAINER = [
        (
            RevisionRange("ad723d6558718e9bbaca930e7e715c9ee754e90e",
                          "HEAD"), get_base_image(ImageBase.DEBIAN_10)
        ),
        (
            _AUTOTOOLS_VERSIONS,
            get_base_image(ImageBase.DEBIAN_10
                          ).run('apt', 'install', '-y', 'autoconf', 'automake')
        ), (_MAKE_VERSIONS, get_base_image(ImageBase.DEBIAN_10))
    ]

    files = ["alice29.txt", "asyoulik.txt", "cp.html", "fields.c", "grammar.lsp", 
             "kennedy.xls", "lcet10.txt", "plrabn12.txt", "ptt5", "sum", "xargs.1"]
    
    configs = [
        ['-5'],
        ['-v -v', '-5'],
        ['-v -v', '-3'],
        ['-v', '-1'],
        ['-9'],
        ['-v -v -v -v', '-3'],
        ['-v', '-3'],
        ['-v', '-9'],
        ['-v', '-7'],
        ['-v -v -v', '-3'],
        ['-v -v -v', '-9'],
        ['-v', '-5'],
        ['-v -v', '-1'],
        ['-v -v', '-9'],
        ['-v -v -v -v', '-9'],
        ['-v -v -v -v', '-7'],
        ['-v -v -v -v', '-1'],
        ['-1'],
        ['-v -v -v -v', '-5'],
        ['-7'],
        ['-v -v -v', '-5'],
        ['-v -v', '-7'],
        ['-v -v -v', '-7'],
        ['-v -v -v', '-1'],
        ['-3'],
        ['--force', '-5'],
        ['--force', '-v -v', '-5'],
        ['--force', '-v -v', '-3'],
        ['--force', '-v', '-1'],
        ['--force', '-9'],
        ['--force', '-v -v -v -v', '-3'],
        ['--force', '-v', '-3'],
        ['--force', '-v', '-9'],
        ['--force', '-v', '-7'],
        ['--force', '-v -v -v', '-3'],
        ['--force', '-v -v -v', '-9'],
        ['--force', '-v', '-5'],
        ['--force', '-v -v', '-1'],
        ['--force', '-v -v', '-9'],
        ['--force', '-v -v -v -v', '-9'],
        ['--force', '-v -v -v -v', '-7'],
        ['--force', '-v -v -v -v', '-1'],
        ['--force', '-1'],
        ['--force', '-v -v -v -v', '-5'],
        ['--force', '-7'],
        ['--force', '-v -v -v', '-5'],
        ['--force', '-v -v', '-7'],
        ['--force', '-v -v -v', '-7'],
        ['--force', '-v -v -v', '-1'],
        ['--force', '-3'],
        ['--quiet', '-5'],
        ['--quiet', '-v -v', '-5'],
        ['--quiet', '-v -v', '-3'],
        ['--quiet', '-v', '-1'],
        ['--quiet', '-9'],
        ['--quiet', '-v -v -v -v', '-3'],
        ['--quiet', '-v', '-3'],
        ['--quiet', '-v', '-9'],
        ['--quiet', '-v', '-7'],
        ['--quiet', '-v -v -v', '-3'],
        ['--quiet', '-v -v -v', '-9'],
        ['--quiet', '-v', '-5'],
        ['--quiet', '-v -v', '-1'],
        ['--quiet', '-v -v', '-9'],
        ['--quiet', '-v -v -v -v', '-9'],
        ['--quiet', '-v -v -v -v', '-7'],
        ['--quiet', '-v -v -v -v', '-1'],
        ['--quiet', '-1'],
        ['--quiet', '-v -v -v -v', '-5'],
        ['--quiet', '-7'],
        ['--quiet', '-v -v -v', '-5'],
        ['--quiet', '-v -v', '-7'],
        ['--quiet', '-v -v -v', '-7'],
        ['--quiet', '-v -v -v', '-1'],
        ['--quiet', '-3'],
        ['--small', '-5'],
        ['--small', '-v -v', '-5'],
        ['--small', '-v -v', '-3'],
        ['--small', '-v', '-1'],
        ['--small', '-9'],
        ['--small', '-v -v -v -v', '-3'],
        ['--small', '-v', '-3'],
        ['--small', '-v', '-9'],
        ['--small', '-v', '-7'],
        ['--small', '-v -v -v', '-3'],
        ['--small', '-v -v -v', '-9'],
        ['--small', '-v', '-5'],
        ['--small', '-v -v', '-1'],
        ['--small', '-v -v', '-9'],
        ['--small', '-v -v -v -v', '-9'],
        ['--small', '-v -v -v -v', '-7'],
        ['--small', '-v -v -v -v', '-1'],
        ['--small', '-1'],
        ['--small', '-v -v -v -v', '-5'],
        ['--small', '-7'],
        ['--small', '-v -v -v', '-5'],
        ['--small', '-v -v', '-7'],
        ['--small', '-v -v -v', '-7'],
        ['--small', '-v -v -v', '-1'],
        ['--small', '-3'],
        ['--force', '--quiet', '-5'],
        ['--force', '--quiet', '-v -v', '-5'],
        ['--force', '--quiet', '-v -v', '-3'],
        ['--force', '--quiet', '-v', '-1'],
        ['--force', '--quiet', '-9'],
        ['--force', '--quiet', '-v -v -v -v', '-3'],
        ['--force', '--quiet', '-v', '-3'],
        ['--force', '--quiet', '-v', '-9'],
        ['--force', '--quiet', '-v', '-7'],
        ['--force', '--quiet', '-v -v -v', '-3'],
        ['--force', '--quiet', '-v -v -v', '-9'],
        ['--force', '--quiet', '-v', '-5'],
        ['--force', '--quiet', '-v -v', '-1'],
        ['--force', '--quiet', '-v -v', '-9'],
        ['--force', '--quiet', '-v -v -v -v', '-9'],
        ['--force', '--quiet', '-v -v -v -v', '-7'],
        ['--force', '--quiet', '-v -v -v -v', '-1'],
        ['--force', '--quiet', '-1'],
        ['--force', '--quiet', '-v -v -v -v', '-5'],
        ['--force', '--quiet', '-7'],
        ['--force', '--quiet', '-v -v -v', '-5'],
        ['--force', '--quiet', '-v -v', '-7'],
        ['--force', '--quiet', '-v -v -v', '-7'],
        ['--force', '--quiet', '-v -v -v', '-1'],
        ['--force', '--quiet', '-3'],
        ['--force', '--small', '-5'],
        ['--force', '--small', '-v -v', '-5'],
        ['--force', '--small', '-v -v', '-3'],
        ['--force', '--small', '-v', '-1'],
        ['--force', '--small', '-9'],
        ['--force', '--small', '-v -v -v -v', '-3'],
        ['--force', '--small', '-v', '-3'],
        ['--force', '--small', '-v', '-9'],
        ['--force', '--small', '-v', '-7'],
        ['--force', '--small', '-v -v -v', '-3'],
        ['--force', '--small', '-v -v -v', '-9'],
        ['--force', '--small', '-v', '-5'],
        ['--force', '--small', '-v -v', '-1'],
        ['--force', '--small', '-v -v', '-9'],
        ['--force', '--small', '-v -v -v -v', '-9'],
        ['--force', '--small', '-v -v -v -v', '-7'],
        ['--force', '--small', '-v -v -v -v', '-1'],
        ['--force', '--small', '-1'],
        ['--force', '--small', '-v -v -v -v', '-5'],
        ['--force', '--small', '-7'],
        ['--force', '--small', '-v -v -v', '-5'],
        ['--force', '--small', '-v -v', '-7'],
        ['--force', '--small', '-v -v -v', '-7'],
        ['--force', '--small', '-v -v -v', '-1'],
        ['--force', '--small', '-3'],
        ['--quiet', '--small', '-5'],
        ['--quiet', '--small', '-v -v', '-5'],
        ['--quiet', '--small', '-v -v', '-3'],
        ['--quiet', '--small', '-v', '-1'],
        ['--quiet', '--small', '-9'],
        ['--quiet', '--small', '-v -v -v -v', '-3'],
        ['--quiet', '--small', '-v', '-3'],
        ['--quiet', '--small', '-v', '-9'],
        ['--quiet', '--small', '-v', '-7'],
        ['--quiet', '--small', '-v -v -v', '-3'],
        ['--quiet', '--small', '-v -v -v', '-9'],
        ['--quiet', '--small', '-v', '-5'],
        ['--quiet', '--small', '-v -v', '-1'],
        ['--quiet', '--small', '-v -v', '-9'],
        ['--quiet', '--small', '-v -v -v -v', '-9'],
        ['--quiet', '--small', '-v -v -v -v', '-7'],
        ['--quiet', '--small', '-v -v -v -v', '-1'],
        ['--quiet', '--small', '-1'],
        ['--quiet', '--small', '-v -v -v -v', '-5'],
        ['--quiet', '--small', '-7'],
        ['--quiet', '--small', '-v -v -v', '-5'],
        ['--quiet', '--small', '-v -v', '-7'],
        ['--quiet', '--small', '-v -v -v', '-7'],
        ['--quiet', '--small', '-v -v -v', '-1'],
        ['--quiet', '--small', '-3'],
        ['--force', '--quiet', '--small', '-5'],
        ['--force', '--quiet', '--small', '-v -v', '-5'],
        ['--force', '--quiet', '--small', '-v -v', '-3'],
        ['--force', '--quiet', '--small', '-v', '-1'],
        ['--force', '--quiet', '--small', '-9'],
        ['--force', '--quiet', '--small', '-v -v -v -v', '-3'],
        ['--force', '--quiet', '--small', '-v', '-3'],
        ['--force', '--quiet', '--small', '-v', '-9'],
        ['--force', '--quiet', '--small', '-v', '-7'],
        ['--force', '--quiet', '--small', '-v -v -v', '-3'],
        ['--force', '--quiet', '--small', '-v -v -v', '-9'],
        ['--force', '--quiet', '--small', '-v', '-5'],
        ['--force', '--quiet', '--small', '-v -v', '-1'],
        ['--force', '--quiet', '--small', '-v -v', '-9'],
        ['--force', '--quiet', '--small', '-v -v -v -v', '-9'],
        ['--force', '--quiet', '--small', '-v -v -v -v', '-7'],
        ['--force', '--quiet', '--small', '-v -v -v -v', '-1'],
        ['--force', '--quiet', '--small', '-1'],
        ['--force', '--quiet', '--small', '-v -v -v -v', '-5'],
        ['--force', '--quiet', '--small', '-7'],
        ['--force', '--quiet', '--small', '-v -v -v', '-5'],
        ['--force', '--quiet', '--small', '-v -v', '-7'],
        ['--force', '--quiet', '--small', '-v -v -v', '-7'],
        ['--force', '--quiet', '--small', '-v -v -v', '-1'],
        ['--force', '--quiet', '--small', '-3'],
    ]

    commands = []
    

    for file in files:
        for i, config in enumerate(configs):
            command = VCommand(
                SourceRoot("xz") / RSBinary("xz"),
                "--keep", # needed for repeating with the same workload
                *config,
                output_param=["{output}"],
                output=SourceRoot("cantrbry.tar.gz/" + file),
                label=file + "-config" + "{:04d}".format(i),
                creates=["cantrbry.tar.gz/" + file + ".bz2"]
            )
            
            
            commands.append(command)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): commands,
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                "--keep",
                # bzip2 compresses very fast even on the best setting, so we
                # need the three input files to get approximately 30 seconds
                # total execution time
                "geo-maps/countries-land-1m.geo.json",
                "geo-maps/countries-land-10m.geo.json",
                "geo-maps/countries-land-100m.geo.json",
                label="med_geo",
                creates=[
                    "geo-maps/countries-land-1m.geo.json.bz2",
                    "geo-maps/countries-land-10m.geo.json.bz2",
                    "geo-maps/countries-land-100m.geo.json.bz2"
                ],
                requires_all_args={"--compress"}
            ),
            VCommand(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                "--keep",
                # bzip2 compresses very fast even on the best setting, so we
                # need the three input files to get approximately 30 seconds
                # total execution time
                "geo-maps-compr/countries-land-1m.geo.json.bz2",
                "geo-maps-compr/countries-land-10m.geo.json.bz2",
                "geo-maps-compr/countries-land-100m.geo.json.bz2",
                label="med_geo",
                creates=[
                    "geo-maps-compr/countries-land-1m.geo.json",
                    "geo-maps-compr/countries-land-10m.geo.json",
                    "geo-maps-compr/countries-land-100m.geo.json"
                ],
                requires_all_args={"--decompress"}
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Bzip2.NAME))

        binary_map.specify_binary(
            'build/bzip2',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "e264a7f7c44fae62f5be9840946f6bc0e8cd6512", "HEAD"
            )
        )
        binary_map.specify_binary(
            'bzip2',
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "33d134030248633ffa7d60c0a35a783c46da034b",
                "e264a7f7c44fae62f5be9840946f6bc0e8cd6512"
            )
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        bzip2_source = Path(self.source_of_primary)
        bzip2_version = ShortCommitHash(self.version_of_primary)
        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        if bzip2_version in typed_revision_range(
            Bzip2._MAKE_VERSIONS, bzip2_source, ShortCommitHash
        ):
            with local.cwd(bzip2_source):
                with local.env(CC=str(cc_compiler)):
                    bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        elif bzip2_version in typed_revision_range(
            Bzip2._AUTOTOOLS_VERSIONS, bzip2_source, ShortCommitHash
        ):
            with local.cwd(bzip2_source):
                with local.env(CC=str(cc_compiler)):
                    bb.watch(local["./autogen.sh"])()
                    bb.watch(local["./configure"])()
                    bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        else:
            (bzip2_source / "build").mkdir(parents=True, exist_ok=True)
            with local.cwd(bzip2_source / "build"):

                with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                    bb.watch(cmake)("..")

                bb.watch(cmake)(
                    "--build", ".", "--config", "Release", "-j",
                    get_number_of_jobs(bb_cfg())
                )
        with local.cwd(bzip2_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        bzip2_source = Path(self.source_of_primary)
        bzip2_version = ShortCommitHash(self.version_of_primary)

        if bzip2_version in typed_revision_range(
            Bzip2._MAKE_VERSIONS, bzip2_source, ShortCommitHash
        ) or bzip2_version in typed_revision_range(
            Bzip2._AUTOTOOLS_VERSIONS, bzip2_source, ShortCommitHash
        ):
            with local.cwd(bzip2_source / "build"):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
        else:
            with local.cwd(bzip2_source / "build"):
                bb.watch(cmake)(
                    "--build", ".", "--config", "Release", "-j",
                    get_number_of_jobs(bb_cfg())
                )

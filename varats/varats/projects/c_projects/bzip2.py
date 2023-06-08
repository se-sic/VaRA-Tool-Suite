"""Project file for xz."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
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

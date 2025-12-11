"""Project file for xz."""
import typing as tp
from enum import Enum
from pathlib import Path
from unittest import TestResult

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.revision_ranges import RevisionRange, GoodBadSubgraph
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
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
from varats.utils.git_util import (
    ShortCommitHash,
    typed_revision_range,
    RepositoryHandle,
)
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_run_testsuite,
    ctest_get_test_names,
)


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

    class Bzip2BuildMethod(Enum):
        MAKE = 0
        AUTOTOOLS = 1
        CMAKE = 2

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                ConfigParams(),
                "--keep",
                # bzip2 compresses very fast even on the best setting, so we
                # need the three input files to get approximately 30 seconds
                # total execution time
                "geo-maps/countries-land-1m.geo.json",
                "geo-maps/countries-land-10m.geo.json",
                "geo-maps/countries-land-100m.geo.json",
                label="med-geo",
                creates=[
                    "geo-maps/countries-land-1m.geo.json.bz2",
                    "geo-maps/countries-land-10m.geo.json.bz2",
                    "geo-maps/countries-land-100m.geo.json.bz2"
                ],
                requires_all_args={"--compress"}
            ),
            VCommand(
                SourceRoot("bzip2") / RSBinary("bzip2"),
                ConfigParams(),
                "--keep",
                # bzip2 compresses very fast even on the best setting, so we
                # need the three input files to get approximately 30 seconds
                # total execution time
                "geo-maps-compr/countries-land-1m.geo.json.bz2",
                "geo-maps-compr/countries-land-10m.geo.json.bz2",
                "geo-maps-compr/countries-land-100m.geo.json.bz2",
                label="med-geo",
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
        binary_map = RevisionBinaryMap(get_local_project_repo(Bzip2.NAME))

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

    def __getbuilddir(self) -> tp.Tuple[Path, Bzip2BuildMethod]:
        """Get the build directory and build method."""
        bzip2_source = local.path(self.source_of_primary)
        bzip2_repo = RepositoryHandle(bzip2_source)
        bzip2_version = ShortCommitHash(self.version_of_primary)

        run_dir: Path
        build_method: Bzip2.Bzip2BuildMethod
        if bzip2_version in typed_revision_range(
            bzip2_repo, Bzip2._MAKE_VERSIONS, ShortCommitHash
        ):
            run_dir = bzip2_source
            build_method = Bzip2.Bzip2BuildMethod.MAKE
        elif bzip2_version in typed_revision_range(
            bzip2_repo, Bzip2._AUTOTOOLS_VERSIONS, ShortCommitHash
        ):
            run_dir = bzip2_source
            build_method = Bzip2.Bzip2BuildMethod.AUTOTOOLS
        else:
            run_dir = bzip2_source / "build"
            build_method = Bzip2.Bzip2BuildMethod.CMAKE

        mkdir("-p", run_dir)
        return run_dir, build_method

    def compile(self) -> None:
        """Compile the project."""
        bzip2_source = Path(self.source_of_primary)
        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir, build_method = self.__getbuilddir()
        if build_method == Bzip2.Bzip2BuildMethod.AUTOTOOLS:
            with local.cwd(build_dir):
                with local.env(CC=str(cc_compiler)):
                    bb.watch(local["./autogen.sh"])()
                    bb.watch(local["./configure"])()

        elif build_method != Bzip2.Bzip2BuildMethod.MAKE:
            with local.cwd(build_dir):
                with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                    bb.watch(cmake)("..")

        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(bzip2_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        bzip2_source = Path(self.source_of_primary)
        bzip2_version = ShortCommitHash(self.version_of_primary)
        bzip2_repo = RepositoryHandle(bzip2_source)

        build_dir, build_method = self.__getbuilddir()
        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def prepare_test_environment(self) -> None:
        """Prepare the testsuite."""
        bzip2_source = Path(self.source_of_primary)
        bzip2_version = ShortCommitHash(self.version_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        cc_compiler = bb.compiler.cc(self)

        build_dir, build_method = self.__getbuilddir()

        if build_method != Bzip2.Bzip2BuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )

        with local.cwd(bzip2_source / "build"):
            with local.env(CXX=str(cpp_compiler), CC=str(cc_compiler)):
                bb.watch(cmake)("test", "-G", "Unix Makefiles", "..")

    def build_tests(self) -> None:
        """Build the tests."""
        bzip2_version_source = local.path(self.source_of_primary)

        build_dir, build_method = self.__getbuilddir()

        if build_method != Bzip2.Bzip2BuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )

        with local.cwd(bzip2_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_get_test_names(build_dir)

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """Run the testsuite."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_run_testsuite(
            build_dir, test_report_path, tests_to_run, tests_to_exclude
        )

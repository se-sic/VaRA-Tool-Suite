"""Project file for brotli."""

import typing as tp
from enum import Enum
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from benchbuild.source.http import HTTPUnzip
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.revision_ranges import (
    RevisionRange,
    SingleRevision,
    block_revisions,
)
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import (
    LUKAS_DICOM_FILES,
    SILESIA_FILES,
    ConfigParams,
    RSBinary,
    WorkloadCategory,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, get_all_revisions_between
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_get_test_names,
    ctest_run_testsuite,
)


class Brotli(VProject):
    """Brotli compression format."""

    NAME = 'brotli'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE: tp.ClassVar = [
        block_revisions(
            [
                RevisionRange(
                    '8f30907d0f2ef354c2b31bdee340c2b11dda0fb0',
                    'e1739826c04a9944672b99b98249dda021bdeb36',
                    'Encoder and Decoder don\'t have a shared Makefile',
                ),
                SingleRevision(
                    "378485b097fd7b80a5e404a3cb912f7b18f78cdb",
                    "Missing required build files",
                ),
            ]
        )(
            PaperConfigSpecificGit(
                project_name="brotli",
                remote="https://github.com/google/brotli.git",
                local="brotli_git",
                refspec="origin/HEAD",
                limit=None,
                shallow=False,
            )
        ),
        FeatureSource(),
        PatchVariationSource(),
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0": "https://github.com/simonepri/geo-maps/releases/"
                "download/v0.6.0"
            },
            files=[
                "countries-land-10km.geo.json",
                "countries-land-2km5.geo.json",
                "countries-land-1km.geo.json",
                "countries-land-500m.geo.json",
                "countries-land-250m.geo.json",
                "countries-land-100m.geo.json",
                "countries-land-10m.geo.json",
                "countries-land-1m.geo.json",
            ],
        ),
        HTTPUnzip(
            local="silesia.zip",
            remote={"1.0": "http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip"},
        ),
        HTTPUnzip(
            local="lukas_2d_16_dicom.zip",
            remote={
                "1.0": "http://www.data-compression.info/files/corpora/lukas_2d_16_dicom.zip"
            },
        ),
        HTTPUnzip(
            local="enwik8.zip",
            remote={"1.0": "https://mattmahoney.net/dc/enwik8.zip"},
        ),
    ]

    WORKLOADS: tp.ClassVar = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-10km.geo.json",
                label="geo-maps-countries-land-10km",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-2km5.geo.json",
                label="geo-maps-countries-land-2km5",
            ),
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-1km.geo.json",
                label="geo-maps-countries-land-1km",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-500m.geo.json",
                label="geo-maps-countries-land-500m",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-250m.geo.json",
                label="geo-maps-countries-land-250m",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                *[f"silesia.zip/{f}" for f in SILESIA_FILES],
                label="silesia",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                *[
                    f"lukas_2d_16_dicom.zip/lukas_2d_16_{f}"
                    for f in LUKAS_DICOM_FILES
                ],
                label="lukas-2d-16-dicom",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "enwik8.zip/enwik8",
                label="enwik8",
            ),
        ],
        WorkloadSet(WorkloadCategory.LARGE): [
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-100m.geo.json",
                label="geo-maps-countries-land-100m",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-10m.geo.json",
                label="geo-maps-countries-land-10m",
            ),
            VCommand(
                SourceRoot("brotli_git") / RSBinary("brotli"),
                "-fkn",
                ConfigParams(),
                "geo-maps/countries-land-1m.geo.json",
                label="geo-maps-countries-land-1m",
            ),
        ],
    }

    class BrotliBuildMethod(Enum):
        MAKE = 0
        CONFIGURE = 1
        CMAKE = 2

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'cmake'
    )

    def __get_build_dir(self) -> tuple[Path, BrotliBuildMethod]:
        """Get the build directory and the build method."""
        brotli_version_source = local.path(self.source_of_primary)
        brotli_repo = get_local_project_repo(self.NAME)
        brotli_version = ShortCommitHash(self.version_of_primary)
        configure_revisions = get_all_revisions_between(
            brotli_repo,
            "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
            "5814438791fb2d4394b46e5682a96b68cd092803",
            ShortCommitHash,
        )
        simple_make_revisions = get_all_revisions_between(
            brotli_repo,
            "e1739826c04a9944672b99b98249dda021bdeb36",
            "378485b097fd7b80a5e404a3cb912f7b18f78cdb",
            ShortCommitHash,
        )
        run_dir: Path
        build_method: Brotli.BrotliBuildMethod
        if brotli_version in simple_make_revisions:
            run_dir = brotli_version_source / "tools"
            build_method = Brotli.BrotliBuildMethod.MAKE
        elif brotli_version in configure_revisions:
            build_method = Brotli.BrotliBuildMethod.CONFIGURE
            run_dir = brotli_version_source
        else:
            build_method = Brotli.BrotliBuildMethod.CMAKE
            run_dir = brotli_version_source / "out"

        mkdir("-p", run_dir)

        return Path(run_dir), build_method

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Brotli.NAME))

        binary_map.specify_binary(
            "out/brotli",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "03739d2b113afe60638069c4e1604dc2ac27380d", "HEAD"
            ),
        )
        binary_map.specify_binary(
            "out/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "5814438791fb2d4394b46e5682a96b68cd092803",
                "03739d2b113afe60638069c4e1604dc2ac27380d",
            ),
        )
        binary_map.specify_binary(
            "bin/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "f9ab24a7aaee93d5932ba212e5e3d32e4306f748",
                "5814438791fb2d4394b46e5682a96b68cd092803",
            ),
        )
        binary_map.specify_binary(
            "tools/bro",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange(
                "e1739826c04a9944672b99b98249dda021bdeb36",
                "378485b097fd7b80a5e404a3cb912f7b18f78cdb",
            ),
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for brotli.

        Note:
            Only supported for revisions using CMake.
        """
        build_dir, method = self.__get_build_dir()
        if method != Brotli.BrotliBuildMethod.CMAKE:
            # Currently unsupported/untested how to run the tests
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )
        with local.cwd(build_dir):
            # Prepare the build directory
            bb.watch(cmake["..", "-G", "Unix Makefiles"])()

    def build_tests(self) -> None:
        """
        Build the tests for brotli.

        Note:
            Only supported for revisions using CMake.
        """
        build_dir, method = self.__get_build_dir()
        if method != Brotli.BrotliBuildMethod.CMAKE:
            # Currently unsupported/untested how to run the tests
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )

        with local.cwd(build_dir):
            # Build the test suite
            bb.watch(make["-j", get_number_of_jobs(bb_cfg())])()

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        Note:
            Only supported for revisions using CMake.
        """
        build_dir, method = self.__get_build_dir()
        if method != Brotli.BrotliBuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )

        return ctest_get_test_names(build_dir)

    def run_testsuite(
        self,
        test_report_path: Path | None = None,
        tests_to_run: tp.Iterable[str] | None = None,
        tests_to_exclude: tp.Iterable[str] | None = None,
    ) -> dict[str, TestResult] | None:
        """
        Executes the test suite for brotli.

        Args:
            test_report_path: Path to store the detailed test results in.
            tests_to_run: List of test cases to run.
                          If None, all tests will be run.

        Returns:
            True if all tests passed, False otherwise.
        """
        build_dir, method = self.__get_build_dir()

        if method != Brotli.BrotliBuildMethod.CMAKE:
            raise NotImplementedError(
                "Test suites are only supported for revisions using CMake."
            )

        return ctest_run_testsuite(
            build_dir, test_report_path, tests_to_run, tests_to_exclude
        )

    def compile(self) -> None:
        """Compile the project."""
        brotli_version_source = local.path(self.source_of_primary)
        c_compiler = bb.compiler.cc(self)

        build_dir, method = self.__get_build_dir()

        with local.cwd(build_dir), local.env(CC=str(c_compiler)):
            if method == Brotli.BrotliBuildMethod.CONFIGURE:
                bb.watch(local["./configure"])()
            if method == Brotli.BrotliBuildMethod.CMAKE:
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(brotli_version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        build_dir, _ = self.__get_build_dir()

        with local.cwd(build_dir):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> list[tuple[str, str]]:
        return [("google", "brotli")]

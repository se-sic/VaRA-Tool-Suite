"""Project file for poppler."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.revision_ranges import block_revisions, RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repo,
    BinaryType,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_commands import download_repo, update_all_submodules
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_run_testsuite,
    ctest_get_test_names,
    TestResult,
)


class Poppler(VProject):
    """Poppler is a free software utility library for rendering Portable
    Document Format documents."""

    NAME = 'poppler'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.RENDERING

    SOURCE = [
        block_revisions([
            RevisionRange(
                "e225b4b804881de02a5d1beb3f3f908a8f8ddc3d",
                "2b2808719d2c91283ae358381391bb0b37d9061d",
                "requiers QT6 which is not easily available"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="poppler",
                remote="https://gitlab.freedesktop.org/poppler/poppler.git",
                local="poppler",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        )
    ]
    TEST_DATA_URL = "https://gitlab.freedesktop.org/poppler/test.git"

    # libcurl4-openssl-dev git ca-certificates locales libgtk-3-dev libbrotli-dev libboost-container-dev qt6-base-dev (from their pipeline)
    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'libfreetype6-dev',
        'libfontconfig-dev', 'libjpeg-dev', 'libopenjp2-7-dev', 'libnss3-dev',
        'libnspr4-dev', 'libtiff-dev', 'libcairo2-dev', 'libboost-dev',
        'liblcms2-dev', 'libcurl4-openssl-dev', 'libpoppler-qt6-dev', 'git',
        'ca-certificates', 'locales', 'openssl', 'pkg-config', 'build-essential'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Poppler.NAME))

        binary_map.specify_binary("libpoppler.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        poppler_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(poppler_version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", ".")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Poppler", "Poppler")]

    # $ git clone --branch ${CI_COMMIT_REF_NAME} --depth 1 ${TEST_DATA_URL} test-data || git clone --depth 1 https://gitlab.freedesktop.org/poppler/test.git test-data
    # Cloning into 'test-data'...
    # $ mkdir -p build && cd build
    # $ cmake -G Ninja -DTESTDATADIR=$PWD/../test-data -DCMAKE_PREFIX_PATH=$PWD/gnupg -DENABLE_UNSTABLE_API_ABI_HEADERS=ON -DVERIFY_PUBLIC_PRIVATE_HEADERS=true ..
    # $ ninja - j ${FDO_CI_CONCURRENT}
    def prepare_test_environment(self) -> None:
        """Prepare the test environment for poppler."""
        poppler_version_source = local.path(self.source_of(self.primary_source))
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", poppler_version_source / "test-data")
        download_repo(poppler_version_source / "test-data", self.TEST_DATA_URL)

        mkdir("-p", poppler_version_source / "build")
        poppler_build = poppler_version_source / "build"

        with local.cwd(poppler_build):
            # git clone the test data look in the ci-pipeline
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)(
                    "-DENABLE_GPGME=OFF", "-DTESTDATADIR=$PWD/../test-data",
                    "-G", "Unix Makefiles", ".."
                )
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def build_tests(self) -> None:
        """Build the tests for poppler."""
        poppler_version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(poppler_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        Returns:
            A list of test names available in the project.
        """
        poppler_version_source = Path(self.source_of_primary)
        return ctest_get_test_names(poppler_version_source)

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """
        Run the test suite for poppler.

        Args:
            test_report_path: Path to store the detailed test results in.
            tests_to_run: List of test cases to run. If None, all tests will be
                          run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            A dictionary mapping test names to their results enum.
        """
        build_dir = Path(self.source_of_primary)
        return ctest_run_testsuite(
            build_dir, test_report_path, tests_to_run, tests_to_exclude
        )

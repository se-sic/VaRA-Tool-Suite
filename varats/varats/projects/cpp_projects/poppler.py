"""Project file for poppler."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
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

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'libfreetype6-dev',
        'libfontconfig-dev', 'libjpeg-dev', 'qt5-default', 'libopenjp2-7-dev',
        'libnss3-dev', 'libnspr4-dev', 'libtiff-dev', 'libcairo2-dev',
        'libboost-dev', 'liblcms2-dev', 'libcurl4-openssl-dev',
        'libpoppler-qt6-dev'
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

    def prepare_test_environment(self) -> None:
        poppler_version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(poppler_version_source):
            # git clone the test data look in the ci-pipeline
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)(
                    "-DENABLE_GPGME=OFF", "-DTESTDATADIR=$PWD/../test-data",
                    "-G", "Unix Makefiles", "."
                )
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def get_test_names(self) -> tp.Iterable[str]:
        poppler_2_version_source = Path(self.source_of_primary)
        return ctest_get_test_names(poppler_2_version_source)

    def build_tests(self) -> None:
        poppler_version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(poppler_version_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        build_dir = Path(self.source_of_primary)
        return ctest_run_testsuite(
            build_dir, test_report_path, tests_to_run, tests_to_exclude
        )

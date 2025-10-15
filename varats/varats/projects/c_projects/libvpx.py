"""Project file for libvpx."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import HTTP
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    WorkloadCategory,
    RSBinary,
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
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_run_testsuite,
    ctest_get_test_names,
    gtest_run_testsuite,
    gtest_get_test_names,
)


class Libvpx(VProject):
    """Codec SDK libvpx (fetched by Git)"""

    NAME = 'libvpx'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="libvpx",
            remote="https://github.com/webmproject/libvpx.git",
            local="libvpx",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTP(
            local="nocturne_aom_sdr_8bit_1080p.y4m",
            remote={
                "1.0":
                    "https://storage.googleapis.com/downloads.webmproject.org/"
                    "AV2Sequences/420_8bit_1080p/"
                    "nocturne_aom_sdr_8540-9009_offset2_420_8bit_1080p.y4m"
            }
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'yasm')

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("libvpx") / RSBinary("vpxenc"),
                "nocturne_aom_sdr_8bit_1080p.y4m",
                "-o",
                "nocturne-1080p",
                ConfigParams(),
                label="nocturne-1080p",
                creates=["nocturne-1080p"]
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Libvpx.NAME))

        binary_map.specify_binary("vpxdec", BinaryType.EXECUTABLE)
        binary_map.specify_binary("vpxenc", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libvpx_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        cxx = bb.compiler.cxx(self)
        with local.cwd(libvpx_source):
            with local.env(CC=str(clang), CXX=str(cxx)):
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        libvpx_source = local.path(self.source_of_primary)

        with local.cwd(libvpx_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("john_koleszar", "libvpx")]

    def prepare_test_environment(self) -> None:
        """Prepare the test environment."""
        libvpx_source = local.path(self.source_of_primary)
        test_source = libvpx_source / "build_tests"
        test_source.mkdir(exist_ok=True)

        clang = bb.compiler.cc(self)
        cxx = bb.compiler.cxx(self)
        with local.cwd(test_source):
            with local.env(CC=str(clang), CXX=str(cxx)):
                configure = local["../configure"]["--disable-examples",
                                                  "--disable-tools",
                                                  "--disable-docs",
                                                  "--enable-unit-tests"]
                # TODO: See how to include perf tests as workloads?
                #"--enable-decode-perf-tests",
                #"--enable-encode-perf-tests"]

                bb.watch(configure)()

            bb.watch(make)("testdata", "-j", get_number_of_jobs(bb_cfg()))

    def build_tests(self):
        libvpx_source = local.path(self.source_of_primary)
        test_source = libvpx_source / "build_tests"

        with local.cwd(test_source):
            bb.watch(make)("test_libvpx", "-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names
            Returns:
                A list of test names available in the test directory.
        """
        test_source = local.path(self.source_of_primary) / "build_tests"
        test_executable = test_source / "test_libvpx"

        return gtest_get_test_names(test_source, test_executable)

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Dict[str, TestResult]:
        """Run the testsuite."""
        libvpx_source = local.path(self.source_of_primary)
        test_source = local.path(self.source_of_primary) / "build_tests"
        test_libvpx = test_source / "test_libvpx"

        return gtest_run_testsuite(
            libvpx_source,
            test_libvpx,
            test_report_path,
            tests_to_run,
            tests_to_exclude=tests_to_exclude,
        )

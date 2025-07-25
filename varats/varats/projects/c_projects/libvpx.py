"""Project file for libvpx."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_run_testsuite,
    ctest_get_test_names,
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
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10
                              ).run('apt', 'install', '-y', 'yasm')

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
        with local.cwd(libvpx_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("john_koleszar", "libvpx")]

    def prepare_test_environment(self) -> None:
        """Prepare the testsuite."""
        libvpx_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(libvpx_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./configure"])()

    def build_tests(self) -> None:
        """Build the tests."""
        libvpx_source = local.path(self.source_of_primary)

        with local.cwd(libvpx_source):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            bb.watch(make)("test")

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names
            Returns:
                A list of test names available in the test directory.
        """
        libvpx_source = local.path(self.source_of_primary)

        try:
            with local.cwd(libvpx_source):
                output = local["./test_libvpx"]["--gtest_list_tests"]
        except ProcessExecutionError:
            return []

        test_names = []

        for line in output.splitlines():
            if not line.strip():
                continue
            if line.endswith('.'):
                current_suite = line.strip().rstrip('.')
                test_names.append(current_suite)

        return test_names

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        """Run the testsuite."""
        libvpx_source = local.path(self.source_of_primary)

        if tests_to_run:
            test_regex = ":".join((test + ".*") for test in tests_to_run)
            with local.cwd(libvpx_source):
                bb.watch(local["./test_libvpx"]["--gtest_filter=" + test_regex])
            return True

        return False

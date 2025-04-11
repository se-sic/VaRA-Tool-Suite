"""Project file for zeromq."""
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import WorkloadCategory, RSBinary
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
from varats.utils.testsuite_utils import (
    ctest_get_test_names,
    ctest_run_testsuite,
)


class Libzmq(VProject):
    """The ZeroMQ lightweight messaging kernel is a library which extends the
    standard socket interfaces with features traditionally provided by
    specialised messaging middleware products."""

    NAME = 'libzmq'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="libzmq",
            remote="https://github.com/zeromq/libzmq.git",
            local="libzmq_git",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run(
        'apt', 'install', '-y', 'cmake', 'build-essential', 'gnutls-dev',
        'libsodium-dev', 'pkg-config'
    )

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("libzmq_git") / RSBinary(f"{binary}"),
                message_size,
                "100000",
                label=f"bench-{binary.replace('_','-')}-{message_size}"
            )
            for message_size in [2**e
                                 for e in range(3, 20)]
            for binary in ["inproc_thr", "inproc_lat"]
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Libzmq.NAME))

        binary_map.specify_binary(
            "build/lib/libzmq.so", BinaryType.SHARED_LIBRARY
        )

        binary_map.specify_binary("build/bin/inproc_thr", BinaryType.EXECUTABLE)

        binary_map.specify_binary("build/bin/inproc_lat", BinaryType.EXECUTABLE)

        binary_map.specify_binary(
            "build/bin/benchmark_radix_tree", BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        libzmq_version_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        cc_compiler = bb.compiler.cc(self)

        mkdir(libzmq_version_source / "build")
        with local.cwd(libzmq_version_source / "build"):
            with local.env(CXX=str(cpp_compiler), CC=str(cc_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(libzmq_version_source):
            verify_binaries(self)

    def recompile(self) -> None:
        """Recompile the project."""
        libzmq_version_source = local.path(self.source_of_primary)

        with local.cwd(libzmq_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Zeromq", "Libzmq")]

    def prepare_test_environment(self) -> None:
        """Prepare the testsuite."""
        version_source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cpp_compiler = bb.compiler.cxx(self)

        with local.cwd(version_source / "build"):
            with local.env(CC=str(cc_compiler), CXX=str(cpp_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")

    def build_tests(self) -> None:
        """Build the tests."""
        libzmq_version_source = local.path(self.source_of_primary)

        with local.cwd(libzmq_version_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        """Get the test names."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_get_test_names(build_dir)

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        """Run the testsuite."""
        build_dir = local.path(self.source_of_primary) / "build"
        return ctest_run_testsuite(build_dir, test_report_path, tests_to_run)

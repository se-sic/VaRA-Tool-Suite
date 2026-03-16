import shutil
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import Git, HTTPUntar
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import WorkloadCategory, RSBinary
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    RevisionBinaryMap,
    get_local_project_repo,
    BinaryType,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    TestResult,
    ctest_get_test_names,
    ctest_run_testsuite,
)


class CryptoMiniSAT(VProject):
    """CryptoMiniSat project."""

    NAME = "cryptominisat"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="cryptominisat",
            remote="https://github.com/msoos/cryptominisat.git",
            local="cryptominisat",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        # The specific combination of branches between cryptominisat, cadical and cadiback
        # is not easy to automatically determine. We follow the current (2026-03) approach from
        # cryptominisats CI, which uses the latest commit on the default branches.
        Git(
            remote="https://github.com/meelgroup/cadical",
            local="cadical",
            refspec="origin/HEAD",
            limit=1,
            shallow=True,
        ),
        Git(
            remote="https://github.com/meelgroup/cadiback",
            local="cadiback",
            refspec="origin/HEAD",
            limit=1,
            shallow=True,
        ),
        HTTPUntar(
            local="traffic_kkb_unknown.cnf",
            remote={
                "1.0":
                    "https://github.com/se-sic/picoSAT-mirror/releases/"
                    "download/picoSAT-965/traffic_kkb_unknown.cnf.tar.gz"
            }
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("cryptominisat") / RSBinary("cryptominisat5"),
                "traffic_kkb_unknown.cnf/traffic_kkb_unknown.cnf",
                label="traffic-kkb-unknown"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12).run('apt', 'install', '-y', 'clang-19', 'libclang-19-dev', 'cmake', 'build-essential', 'help2man', 'libgmp-dev')\
                                                        .run("update-alternatives", "--install", "/usr/bin/clang", "clang", "/usr/bin/clang-19", "100") \
                                                        .run("update-alternatives", "--install", "/usr/bin/clang++", "clang++", "/usr/bin/clang++-19", "100") \
                                                        .run("update-alternatives", "--set", "clang", "/usr/bin/clang-19") \
                                                        .run("update-alternatives", "--set", "clang++", "/usr/bin/clang++-19")

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List['ProjectBinaryWrapper']:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(CryptoMiniSAT.NAME)
        )

        binary_map.specify_binary(
            "build/cryptominisat5",
            BinaryType.EXECUTABLE,
            valid_exit_codes=[0, 10, 20]
        )

        return binary_map[revision]

    def compile(self) -> None:
        # Multiple steps required:
        # 1. Build cadical
        # 2. Build cadiback
        # 3. Build cryptominisat with the built cadical and cadiback

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir = Path(self.builddir)
        crypto_src = Path(self.source_of_primary)
        cadical_src = Path(self.source_of("cadical"))
        cadiback_src = Path(self.source_of("cadiback"))

        cmake = local["cmake"]
        make = local["make"]
        with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):

            with local.cwd(cadical_src):
                with local.env(CXXFLAGS="-fPIC"):
                    bb.watch(local["./configure"])()
                    bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            with local.cwd(cadiback_src):
                bb.watch(local["./configure"])()
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            # Copy so files into lib dir of cryptominisat to link against
            (build_dir / "lib").mkdir(exist_ok=True)
            (crypto_src / "build").mkdir(exist_ok=True)

            shutil.copy(cadical_src / "build/libcadical.so", build_dir / "lib")
            shutil.copy(cadiback_src / "libcadiback.so", build_dir / "lib")
            shutil.copy(cadical_src / "build/libcadical.so", build_dir)
            shutil.copy(cadiback_src / "libcadiback.so", build_dir)
            shutil.copy(
                cadical_src / "build/libcadical.so", crypto_src / "build"
            )
            shutil.copy(cadiback_src / "libcadiback.so", crypto_src / "build")

            with local.cwd(crypto_src / "build"):
                with local.env(LD_LIBRARY_PATH=str(build_dir / "lib")):
                    bb.watch(cmake
                            )("-DENABLE_TESTING=ON", "-DIPASIR=ON", "-S", "..")
                    bb.watch(cmake)(
                        "--build", ".", "-j", get_number_of_jobs(bb_cfg())
                    )

    def recompile(self) -> None:
        build_dir = Path(self.builddir) / "build"
        with local.env(LD_LIBRARY_PATH=str(build_dir / "lib")):
            with local.cwd(Path(self.source_of_primary) / "build"):
                cmake = local["cmake"]
                bb.watch(cmake
                        )("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

    def run_tests(self) -> None:
        pass

    ##############################
    # SupportsTestSuite Protocol #
    ##############################

    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for this project.

        After running this method, the test environment should be prepared such
        that tests are discoverable for the get_test_names() method. This does
        not necessarily mean that the tests are built yet.
        """
        self.compile()

    def build_tests(self) -> None:
        """
        Build the tests for this project.

        Should be called after prepare_test_environment() to build the tests.
        Once this method is called, the tests should be built and ready to run.
        """
        self.recompile()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """
        Run the test suite for this project.

        Args:
            test_report_path: Path to the test report file.
            tests_to_run: List of test cases to run.
                          If None, all tests will be run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            returns a dictionary mapping test names to respective result (e.g., 'passed', 'failed', 'skipped').
        """
        return ctest_run_testsuite(
            build_dir=Path(self.version_of_primary) / "build",
            test_report_path=test_report_path,
            tests_to_run=tests_to_run,
            tests_to_exclude=tests_to_exclude
        )

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project in the current
        revision and configuration. Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        build_dir = Path(self.version_of_primary) / "build"

        return ctest_get_test_names(build_dir)

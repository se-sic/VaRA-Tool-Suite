import shutil
import typing
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import SourceRoot, WorkloadSet
from benchbuild.source import Git, HTTPMultiple
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.patch_variation_source import PatchVariationSource
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    RevisionBinaryMap,
    get_local_project_repo, ProjectBinaryWrapper,
)
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RepositoryHandle, RepositoryAtCommit
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

    SOURCE: typing.ClassVar = [
        PaperConfigSpecificGit(
            project_name="cryptominisat",
            remote="https://github.com/msoos/cryptominisat.git",
            local="cryptominisat",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        ),
        PatchVariationSource(),
        # The specific combination of branches between
        # cryptominisat, cadical and cadiback
        # is not easy to automatically determine.
        # One needs to clearly specify the correct commits when running the experiments.
        # Known working combination:
        # cryptominisat: ...
        # cadical: 729939aba815b1837b1590279e66c61ed9d3092f
        # cadiback: a44d5a94c8b8c2c4c8c77116ce80d2bb3a974252
        Git(
            remote="https://github.com/meelgroup/cadical",
            local="cadical-cms",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        ),
        Git(
            remote="https://github.com/meelgroup/cadiback",
            local="cadiback-cms",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
        ),
        HTTPMultiple(
            local="main2024",
            remote={
                "1.0": "https://github.com/se-sic/picoSAT-vara/releases/download/workloads-main-2024-hc/"
            },
            files=[
                "heule-noL-11-12.sanitized.cnf",
                "mp1-ps-5000.cnf",
                "stable-300.cnf",
            ]
        ),
    ]

    WORKLOADS: typing.ClassVar = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("cryptominisat") / RSBinary("cryptominisat5"),
                "main2024/heule-noL-11-12.sanitized.cnf",
                label="heule-noL-11-12",
            ),
            VCommand(
                SourceRoot("cryptominisat") / RSBinary("cryptominisat5"),
                "main2024/mp1-ps-5000.cnf",
                label="mp1-ps-5000",
            ),
            VCommand(
                SourceRoot("cryptominisat") / RSBinary("cryptominisat5"),
                "main2024/stable-300.cnf",
                label="stable-300",
            ),
        ]
    }

    CONTAINER = (
        get_base_image(ImageBase.DEBIAN_12)
        .run(
            'apt',
            'install',
            '-y',
            'clang-19',
            'libclang-19-dev',
            'cmake',
            'build-essential',
            'help2man',
            'libgmp-dev',
        )
        .run(
            "update-alternatives",
            "--install",
            "/usr/bin/clang",
            "clang",
            "/usr/bin/clang-19",
            "100",
        )
        .run(
            "update-alternatives",
            "--install",
            "/usr/bin/clang++",
            "clang++",
            "/usr/bin/clang++-19",
            "100",
        )
        .run("update-alternatives", "--set", "clang", "/usr/bin/clang-19")
        .run("update-alternatives", "--set", "clang++", "/usr/bin/clang++-19")
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash,
    ) -> list[ProjectBinaryWrapper]:
        """Returns the binaries for a given revision."""
        binary_map = RevisionBinaryMap(
            get_local_project_repo(CryptoMiniSAT.NAME)
        )

        binary_map.specify_binary(
            "build/cryptominisat5",
            BinaryType.EXECUTABLE,
            valid_exit_codes=[0, 10, 20],
        )

        return binary_map[revision]

    def compile(self) -> None:
        """
        Compile the project.

        Requires multiple steps:
            1. Build cadical
            2. Build cadiback
            3. Build cryptominisat with the built cadical and cadiback
        """
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        build_dir = Path(self.builddir)
        crypto_src = Path(self.source_of_primary)
        cadical_src = Path(self.source_of("cadical-cms"))
        cadiback_src = Path(self.source_of("cadiback-cms"))

        # Create SymLinks for build scripts
        (build_dir / "cadical").symlink_to(cadical_src)
        (build_dir / "cadiback").symlink_to(cadiback_src)

        cmake = local["cmake"]
        make = local["make"]
        with (local.env(CC=str(c_compiler), CXX=str(cxx_compiler))):
            with local.cwd(cadical_src), local.env(CXXFLAGS="-fPIC"):
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

            with local.cwd(crypto_src / "build"), \
                 local.env(LD_LIBRARY_PATH=str(build_dir / "lib")):
                    bb.watch(cmake)(
                        "-DENABLE_TESTING=ON", "-DIPASIR=ON", "-S", ".."
                    )
                    bb.watch(cmake)(
                        "--build", ".", "-j", get_number_of_jobs(bb_cfg())
                    )

    def recompile(self) -> None:
        """Recompile the project."""
        build_dir = Path(self.builddir) / "build"
        with local.env(LD_LIBRARY_PATH=str(build_dir / "lib")), \
             local.cwd(Path(self.source_of_primary) / "build"):
                cmake = local["cmake"]
                bb.watch(cmake)(
                    "--build", ".", "-j", get_number_of_jobs(bb_cfg())
                )

    def run_tests(self) -> None:  # noqa: D102
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
        test_report_path: Path | None = None,
        tests_to_run: tp.Iterable[str] | None = None,
        tests_to_exclude: tp.Iterable[str] | None = None,
    ) -> dict[str, TestResult] | None:
        """
        Run the test suite for this project.

        Args:
            test_report_path: Path to the test report file.
            tests_to_run: List of test cases to run.
                          If None, all tests will be run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            returns a dictionary mapping test names to respective result
            (e.g., 'passed', 'failed', 'skipped').
        """
        return ctest_run_testsuite(
            build_dir=Path(self.source_of_primary) / "build",
            test_report_path=test_report_path,
            tests_to_run=tests_to_run,
            tests_to_exclude=tests_to_exclude,
        )

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Returns a list of tests that can be run for this project.

        Requires that prepare_test_environment() was
        called before.

        Returns:
             A list of tests available for this project.
        """
        build_dir = Path(self.source_of_primary) / "build"

        return ctest_get_test_names(build_dir)

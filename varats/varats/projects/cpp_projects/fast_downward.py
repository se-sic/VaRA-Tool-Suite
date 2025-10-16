"""Project file for FastDownward."""
import re
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import cmake, mkdir, pytest
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_repo,
    get_tagged_commits,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import FullCommitHash, ShortCommitHash
from varats.utils.settings import bb_cfg


class FastDownward(VProject, ReleaseProviderHook):
    """Planning tool FastDownward (fetched by Git)"""

    NAME = 'FastDownward'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.PLANNING

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="FastDownward",
            remote="https://github.com/aibasel/downward.git",
            local="FastDownward",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_12
    ).run('apt', 'install', '-y', 'cmake', 'g++', 'git', 'make', 'python3')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(FastDownward.NAME)
        )
        binary_map.specify_binary(
            'build/release/bin/downward', BinaryType.EXECUTABLE
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for fast downward.

        Note:
            Fast Downward requires tests to be built to also collect the test
            names.
        """
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", version_source / "builds/release")
        mkdir("-p", version_source / "builds/debug")

        build_types = ["Release", "Debug"]
        for build_type in build_types:
            with local.cwd(version_source / "builds" / build_type.lower()):
                with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                    bb.watch(cmake
                            )("../../src", f"-DCMAKE_BUILD_TYPE={build_type}")

                bb.watch(cmake
                        )("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

    def build_tests(self) -> None:
        """
        Builds the test environment for fast downward.

        Note:
            Fast Downward requires tests to be built to also collect the test
            names. Therefore, this method just calls the prepare method.
        """
        self.prepare_test_environment()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        """
        Run the test suite for fast downward.

        Args:
            test_report_path: Path to store the detailed test results in.
            tests_to_run: List of test cases to run. If None, all tests will be
                          run.

        Returns:
            True if all tests passed, False otherwise.
        """
        if tests_to_run is None:
            # In case no test names are given, we run all tests
            tests_to_run = []

        version_source = local.path(self.source_of(self.primary_source))

        # "test_commandline_args" requires the external plan validator VAL
        # to be installed.
        # Since this is usually not the case, we skip this test
        test_runner = pytest["-k", "not test_commandline_args"]
        if tests_to_exclude:
            exclude_regex = ' and '.join([
                f"'not {re.escape(name)}'" for name in tests_to_exclude
            ])
            test_runner = test_runner["-k", f"not ({exclude_regex})"]

        if test_report_path:
            test_runner = test_runner["--junitxml", test_report_path]

        with local.cwd(version_source):
            ret_code: int
            test_args = ["driver/tests.py", *tests_to_run]
            ret_code, _, _ = bb.watch(test_runner[test_args])()

        return ret_code == 0

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        Returns:
            A list of test names available in the project.
        """
        pytest_cmd = pytest["--collect-only", "-q", "driver/tests.py"]

        try:
            with local.cwd(self.source_of(self.primary_source)):
                _, output, _ = bb.watch(pytest_cmd)()
        except ProcessExecutionError:
            return []

        # For some reason even during the collection phase, FastDownward
        # is executed.
        # Therefore, some output from the planning tool is included in stdout
        # All test name lines start with "driver/tests.py::"
        test_names = [
            line.strip()
            for line in output.splitlines()
            if line.startswith("driver/tests.py::")
        ]

        return test_names

    def compile(self) -> None:
        """Compile the project."""
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", version_source / "builds/release")

        with local.cwd(version_source / "builds/release"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("../../src", f"-DCMAKE_BUILD_TYPE=Release")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        repo_loc = get_local_project_repo(cls.NAME)
        with local.cwd(repo_loc):
            # Before 2019_07, there were no real releases, but the following
            # commits were identified as suitable.
            release_commits = {
                (
                    FullCommitHash('e4eb64c613ae34b97ab9409deac5331ec2ce5e43'),
                    'release-16.07.0'
                ),
                (
                    FullCommitHash('91f44fa59ea57014a7769062a92aa752f503128e'),
                    'release-17.01.0'
                ),
                (
                    FullCommitHash('363e2fc9a8b7adb48b4c30e929097798928c7370'),
                    'release-17.07.0'
                ),
                (
                    FullCommitHash('0e8acd2f2613e032040dc6b6d4bf1926848aa4cb'),
                    'release-18.01.0'
                ),
                (
                    FullCommitHash('dd7ddfeea72a699d381dce35657d683259be77c0'),
                    'release-18.07.0'
                ),
                (
                    FullCommitHash('2cc2a66e8073a73571e0a37cd806380f13751a7c'),
                    'release-19.01.0'
                )
            }

            tagged_commits = get_tagged_commits(cls.NAME)
            release_commits = release_commits.union({
                (FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match("^release-[0-9]+\\.[0-9]+\\.[0-9]+$", tag)
            })

            return list(release_commits)

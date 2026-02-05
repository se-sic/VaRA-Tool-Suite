"""Project file for redis."""
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

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
    TestResult,
)


class Redis(VProject):
    """
    Redis is an in-memory database that persists on disk.

    (fetched by Git)
    """

    NAME = 'redis'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.DATABASE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="redis",
            remote="https://github.com/antirez/redis.git",
            local="redis",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Redis.NAME))

        binary_map.specify_binary(
            'src/redis-server',
            BinaryType.EXECUTABLE,
            override_binary_name='redis_server'
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        redis_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(redis_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("Redislabs", "Redis")]

    def prepare_test_environment(self) -> None:
        pass

    def build_tests(self) -> None:
        """
        Build the tests for redis.

        Note:
            as redis uses a custom test suite, the test environment are
            already prepared and only need to be built.
        """
        redis_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(redis_source):
            with local.env(CC=str(clang)):
                bb.watch(make)("test", "-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        Returns:
            A list of test names available in the project.
        """
        redis_source = local.path(self.source_of_primary)

        clang = bb.compiler.cc(self)
        with local.cwd(redis_source):
            with local.env(CC=str(clang)):
                runtest = local["./runtest"]
                ret_code, out, err = bb.watch(runtest)("--list-tests")

        test_names = out.splitlines()
        return test_names

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        """
        Run the test suite for redis.

        Args:
            test_report_path: Path to store the detailed test results in.
            tests_to_run: List of test cases to run. If None, all tests will be
                          run.
            tests_to_exclude: List of test cases to exclude.

        Returns:
            A dictionary mapping test names to their results enum.

        Note:
            The redis provided test suite is somewhat broken when run with
            VaRA-TS beecause of length of path for certain port.
        """
        redis_source = local.path(self.source_of_primary)

        args: tp.List[str] = []
        if tests_to_run:
            for test in tests_to_run:
                args.extend(["--single", test])

        with local.cwd(redis_source):
            runtest = local["./runtest"]
            ret_code, out, err = bb.watch(runtest)(*args)

        res = out.split("The End")[1]

        result = self.parse_res(res)

        return result

    def parse_res(self, tests: tp.Optional[tp.Iterable[str]]):
        """
        " Parse the test results from redis test suite.

        Args:
            tests: Optional list of test names to filter for.

        Returns:
            A dictionary mapping test names to their results enum.
        """
        results: tp.Dict[str, TestResult] = {}
        for line in tests.splitlines():
            if tests and not any(test in line for test in tests):
                continue
            if " - " in line:
                test_name = line.split()[1]
                results[test_name] = TestResult.PASSED
            elif "FAIL" in line:
                test_name = line.split()[0]
                results[test_name] = TestResult.FAILED
        return results

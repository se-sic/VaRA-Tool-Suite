"""Project file for Z3."""
import re
import typing as tp
from pathlib import Path
from typing import List

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.experiment_util import ZippedReportFolder
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_repo,
    verify_binaries,
    get_tagged_commits,
    RevisionBinaryMap,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import ShortCommitHash, FullCommitHash
from varats.utils.settings import bb_cfg
from varats.utils.testsuite_utils import (
    ctest_run_testsuite,
    ctest_get_test_names,
    TestResult,
)


class Z3(VProject, ReleaseProviderHook):
    """Z3 is a theorem prover from Microsoft Research."""

    NAME = 'z3'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.SOLVER

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="z3",
            remote="https://github.com/Z3Prover/z3.git",
            local="z3",
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
        binary_map = RevisionBinaryMap(get_local_project_repo(Z3.NAME))
        binary_map.specify_binary('build/z3', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        z3_source = Path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        (z3_source / "build").mkdir(parents=True, exist_ok=True)

        with local.cwd(z3_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "../")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))
        with local.cwd(z3_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        major_release_regex = "^(z|Z)3-[0-9]+\\.[0-9]+\\.0$"
        minor_release_regex = "^(z|Z)3-[0-9]+\\.[0-9]+(\\.[1-9]+)?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.MAJOR:
            return [(FullCommitHash(h), tag)
                    for h, tag in tagged_commits
                    if re.match(major_release_regex, tag)]
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)]

    def prepare_test_environment(self) -> None:
        z3_source = Path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        (z3_source / "build").mkdir(parents=True, exist_ok=True)

        with local.cwd(z3_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "../")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

    def build_tests(self) -> None:
        z3_source = Path(self.source_of(self.primary_source))

        (z3_source / "build").mkdir(parents=True, exist_ok=True)

        with local.cwd(z3_source / "build"):
            bb.watch(make)("test-z3", "-j", get_number_of_jobs(bb_cfg()))

    def get_test_names(self) -> tp.Iterable[str]:
        z3_source = Path(self.source_of(self.primary_source))
        z3_build = z3_source / "build"

        test_names = []
        with local.cwd(z3_build):
            runtests = local["./test-z3"]
            ret_code, out, err = bb.watch(runtests)()

        modules = out.split("Module names:")[1]
        for line in modules.splitlines():
            test_name = line.strip()
            if test_name:
                test_names.append(test_name)

        return test_names

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None
    ) -> tp.Optional[tp.Dict[str, TestResult]]:
        z3_source = Path(self.source_of(self.primary_source))
        if not tests_to_run:
            tests_to_run = self.get_test_names()
        results: tp.Dict[str, TestResult] = {}
        if test_report_path:
            aggregated_results = test_report_path / "aggregated_test_results.zip"
        else:
            aggregated_results = z3_source / "aggregated_test_results.zip"

        runtest: List[str] = []
        if not tests_to_exclude is None:
            for test in tests_to_run:
                if not test in tests_to_exclude:
                    runtest.append(test)

        with ZippedReportFolder(aggregated_results) as zip_folder:
            for test in tests_to_run:
                test_report = Path(zip_folder) / f"{test}-tests.txt"
                with local.cwd(z3_source / "build"):
                    local["./test-z3"](test, f" > {test_report}")

                f = open(test_report, "r")
                res = f.read()
                f.close()
                if "PASS" in res:
                    results[test] = TestResult.PASSED
                else:
                    results[test] = TestResult.FAILED

        return results

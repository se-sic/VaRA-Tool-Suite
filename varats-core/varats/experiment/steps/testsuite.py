"""
Project Steps for interacting with the TestSuite protocol.

This allows to prepare, build and run test suites for projects
"""
import json
import textwrap
import typing as tp
from pathlib import Path

from benchbuild.utils.actions import ProjectStep, StepResult
from plumbum import ProcessExecutionError

from varats.experiment.experiment_util import AsOutputFolderStep
from varats.project.varats_project import VProject, SupportsTestSuites
from varats.utils.testsuite_utils import TestResult


class PrepareTestSuite(ProjectStep):  # type: ignore
    """Experiment step to prepare the test suite for a project."""
    project: VProject

    NAME = "PrepareTestSuite"
    DESCRIPTION = "Prepare the in-built test-suite of the project"

    def __init__(self, project: VProject):
        super().__init__(project)

    def __call__(self) -> StepResult:
        if not isinstance(self.project, SupportsTestSuites):
            raise TypeError(
                f"Project {self.project.name} does not support testing."
            )
        try:
            self.project.prepare_test_environment()
            self.status = StepResult.OK
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Prepare test-suite", indent * " "
        )


class BuildTestSuite(ProjectStep):  # type: ignore
    """Experiment step to build the test suite for a project."""
    project: VProject

    NAME = "BuildTestSuite"
    DESCRIPTION = "Build the in-built test-suite of the project"

    def __init__(self, project: VProject):
        super().__init__(project)

    def __call__(self) -> StepResult:
        if not isinstance(self.project, SupportsTestSuites):
            raise TypeError(
                f"Project {self.project.name} does not support testing."
            )
        try:
            self.project.build_tests()
            self.status = StepResult.OK
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Build test-suite", indent * " "
        )


def _parse_results(result: tp.Dict[str, TestResult]) -> bool:
    result_filter = {
        TestResult.PASSED: True,
        TestResult.FAILED: True,
        TestResult.SKIPPED: True,
        TestResult.TIMEOUT: True,
        TestResult.DISABLED: True,
        TestResult.UNKNOWN: True,
    }
    return all(result_filter.get(status) == True for status in result.values())


@AsOutputFolderStep("__output_path")
class RunTestSuite(ProjectStep):  # type: ignore
    """Experiment step to run the test suite on a project."""
    project: VProject

    NAME = "RunTestSuite"
    DESCRIPTION = "Run the in-built test-suite of the project"

    def __init__(
        self,
        project: VProject,
        output_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None,
        tests_to_exclude: tp.Optional[tp.Iterable[str]] = None,
        result_filter: tp.Optional[tp.Callable[[tp.Dict[str, TestResult]],
                                               bool]] = None
    ):
        """
        Initialize the test-suite step.

        Args:
          project: Project to run the test-suite on
          output_path: Path to write the test report file to
        """
        super().__init__(project)
        self.__output_path = output_path
        self.__tests_to_run = tests_to_run
        if result_filter is not None:
            self.__result_filter = result_filter
        else:
            self.__result_filter = _parse_results
        self.__tests_to_run = tests_to_run
        self.__tests_to_exclude = tests_to_exclude

    @property
    def output_path(self) -> Path:
        return self.__output_path

    def set_output_path(self, output_path: Path) -> None:
        self.__output_path = output_path

    def __call__(self) -> StepResult:
        if not isinstance(self.project, SupportsTestSuites):
            raise TypeError(
                f"Project {self.project.name} does not support testing."
            )
        try:
            self.project.prepare_test_environment()
            results = self.project.run_testsuite(
                tests_to_run=self.__tests_to_run,
                tests_to_exclude=self.__tests_to_exclude
            )
            status = self.__result_filter(results)
            if status:

                def encode_test_result(obj: tp.Any) -> tp.Any:
                    if isinstance(obj, TestResult):
                        return obj.name
                    raise TypeError(
                        f"Object of type {obj.__class__.__name__} is not JSON serializable"
                    )

                with open(self.__output_path, 'w') as f:
                    json.dump(results, f, default=encode_test_result)
                self.status = StepResult.OK
            else:
                self.status = StepResult.ERROR
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run test-suite", indent * " "
        )


class CollectTests(ProjectStep):  # type: ignore
    """Experiment step to collect the test suite for a project."""
    project: VProject

    NAME = "CollectTests"
    DESCRIPTION = "Collect the in-built test-suite of the project"

    def __init__(self, project: VProject, output_path: Path):
        super().__init__(project)
        self.__output_path = output_path

    def __call__(self) -> StepResult:
        if not isinstance(self.project, SupportsTestSuites):
            raise TypeError(
                f"Project {self.project.name} does not support testing."
            )
        try:
            tests = self.project.get_test_names()
            self.status = StepResult.OK
        except ProcessExecutionError as pe:
            print(
                f"Error while collecting tests for project {self.project.name}: {pe}"
            )
            self.status = StepResult.ERROR
            tests = []

        print(f"Collected tests: {tests}")

        with open(self.__output_path, 'w') as f:
            for test in tests:
                f.write(f"{test}\n")

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Collect test names", indent * " "
        )

"""
Project Steps for interacting with the TestSuite protocol.

This allows to prepare, build and run test suites for projects
"""
import textwrap
import typing as tp
from pathlib import Path

from benchbuild.utils.actions import ProjectStep, StepResult
from plumbum import ProcessExecutionError

from varats.project.varats_project import VProject, SupportsTestSuites


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
        test_to_include: tp.Optional[tp.Iterable[str]] = None,
        test_to_exclude: tp.Optional[tp.Iterable[str]] = None
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
        self.__test_to_include = test_to_include
        self.__test_to_exclude = test_to_exclude

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
            result_status, results = self.project.run_testsuite(
                self.__output_path, self.__tests_to_run, self.__test_to_include,
                self.__test_to_exclude
            )
            if result_status:
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
        except ProcessExecutionError:
            self.status = StepResult.ERROR
            tests = []

        print(f"Collected tests: {tests}")

        with open(self.__output_path, 'w') as f:
            for test in tests:
                f.write(f"{test}\n")

        return self.status

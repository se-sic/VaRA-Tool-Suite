import textwrap
import typing as tp
from pathlib import Path

from benchbuild.utils.actions import ProjectStep, StepResult
from plumbum import ProcessExecutionError

from varats.project.varats_project import VProject, SupportsTesting


class Testsuite(ProjectStep):
    """Experiment step to run the test suite on a project."""
    project: VProject

    NAME = "TESTSUITE"
    DESCRIPTION = "Run the in-built test-suite of the project"

    def __init__(
        self,
        project: VProject,
        output_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
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

    def __call__(self, *args, **kwargs):
        if not isinstance(self.project, SupportsTesting):
            raise TypeError(
                f"Project {self.project.name} does not support testing."
            )
        try:
            result = self.project.run_testsuite(
                self.__output_path, self.__tests_to_run
            )
            if result:
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

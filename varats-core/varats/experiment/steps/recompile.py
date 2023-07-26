"""Recompilation support for experiments."""
import textwrap

from benchbuild.utils.actions import ProjectStep, StepResult
from plumbum import ProcessExecutionError


class ReCompile(ProjectStep):
    """Experiment step to recompile a project."""

    NAME = "RECOMPILE"
    DESCRIPTION = "Recompile the project"

    def __call__(self) -> StepResult:
        try:
            if hasattr(self.project, "recompile"):
                self.project.recompile()
            else:
                raise NotImplementedError(
                    f"{self.project} does not implement 'recompile'."
                )

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        self.status = StepResult.OK

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Recompile", indent * " "
        )

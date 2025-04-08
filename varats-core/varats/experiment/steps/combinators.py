"""Collection of combinator experiment steps."""
import textwrap
import typing as tp
from pathlib import Path

from benchbuild.utils.actions import StepResult, ProjectStep

from benchbuild import Project
from varats.experiment.experiment_util import OutputFolderStep


def _run_with_output_if_necessary(
    tmp_dir: Path, step: ProjectStep
) -> StepResult:
    if isinstance(step, OutputFolderStep):
        return step.call_with_output_folder(tmp_dir)

    return step()


class IfThenElse(OutputFolderStep):
    """
    Step that executes one of two sub steps based on a condition.

    This step implements both interfaces for ProjectSteps and OutputFolderSteps.
    """

    def __init__(
        self,
        project: Project,
        condition: ProjectStep,
        valid_results: tp.Optional[tp.List[StepResult]] = None,
        then_step: tp.Optional[ProjectStep] = None,
        else_step: tp.Optional[ProjectStep] = None
    ) -> None:
        super().__init__(project)
        self.__condition = condition
        self.__then_step = then_step
        self.__else_step = else_step
        if valid_results is None:
            self.__valid_results = [StepResult.OK, StepResult.CAN_CONTINUE]
        else:
            self.__valid_results = valid_results

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        result = _run_with_output_if_necessary(tmp_dir, self.__condition)

        if result in self.__valid_results:
            run_step = self.__then_step
        else:
            run_step = self.__else_step

        if not run_step:
            return result

        return _run_with_output_if_necessary(tmp_dir, run_step)

    def __call__(self) -> StepResult:
        result = self.__condition()

        if result in self.__valid_results:
            run_step = self.__then_step
        else:
            run_step = self.__else_step

        if not run_step:
            return result

        return run_step()

    def __str__(self, indent: int = 0) -> str:
        outstr = textwrap.indent("* If: ", indent * " ") + "\n"
        outstr += textwrap.indent(
            str(self.__condition), (indent + 2) * " "
        ) + "\n"

        if self.__then_step:
            outstr += textwrap.indent("* Then: ", indent * " ") + "\n"
            outstr += textwrap.indent(
                str(self.__then_step), (indent + 2) * " "
            ) + "\n"

        if self.__else_step:
            outstr += textwrap.indent("* Else: ", indent * " ") + "\n"
            outstr += textwrap.indent(
                str(self.__else_step), (indent + 2) * " "
            ) + "\n"
        return outstr

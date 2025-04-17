"""Collection of combinator experiment steps."""
import textwrap
import typing as tp
from pathlib import Path

from benchbuild.project import Project
from benchbuild.utils.actions import ProjectStep, StepResult

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
        then_step: tp.Optional[ProjectStep] = None,
        else_step: tp.Optional[ProjectStep] = None,
        valid_results: tp.Optional[tp.List[StepResult]] = None,
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


class OutputAdapter(OutputFolderStep):
    """Wraps a step in order to make it compatible with OutputFolderStep."""

    def __init__(
        self,
        project: Project,
        step: ProjectStep,
        out_path_adapter: tp.Optional[tp.Callable[[ProjectStep, Path],
                                                  None]] = None
    ) -> None:
        """
        Wraps a step in order to make it compatible with OutputFolderStep.

        Args:
            step: The step to wrap.
            out_path_adapter: A callable that takes the step and a path and
                            modifies the step to use that path.
        """
        super().__init__(project)
        self.__step = step
        self.__out_path_adapter = out_path_adapter

    def call_with_output_folder(self, tmp_dir: Path) -> StepResult:
        if self.__out_path_adapter:
            self.__out_path_adapter(self.__step, tmp_dir)

        return _run_with_output_if_necessary(tmp_dir, self.__step)

    def __str__(self, indent: int = 0) -> str:
        return str(self.__step) + "(Wrapped)"

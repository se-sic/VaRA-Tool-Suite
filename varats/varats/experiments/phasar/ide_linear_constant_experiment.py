"""Module for phasar LinearConstantAnalysis analyses."""
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    wrap_unlimit_stack_size,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    get_varats_result_folder,
    exec_func_with_pe_error_handler,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filename,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.report.report import ReportSpecification


class IDELinearConstantAnalysis(actions.Step):  # type: ignore
    """Analysis step to run phasar's IDELinearConstantAnalysis on a project."""

    NAME = "IDELinearConstantAnalysis"
    DESCRIPTION = (
        "Flow- and context-sensitive analysis that tracks constant "
        "variables and variables that linearly depend on constant "
        "values through the program."
    )

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle

    def analyze(self) -> actions.StepResult:
        """Run phasar's IDELinearConstantAnalysis analysis."""
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        varats_result_folder = get_varats_result_folder(project)

        phasar = local["phasar-llvm"]
        for binary in project.binaries:
            bc_file = get_cached_bc_file_path(project, binary)

            result_file = create_new_success_result_filename(
                self.__experiment_handle, EmptyReport, project, binary
            )

            phasar_params = ["-m", bc_file, "-C", "CHA", "-D", "ide-lca"]

            run_cmd = wrap_unlimit_stack_size(phasar[phasar_params])

            run_cmd = (run_cmd > f'{varats_result_folder}/{result_file}')

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, EmptyReport,
                    Path(varats_result_folder)
                )
            )

        return actions.StepResult.OK


class IDELinearConstantAnalysisExperiment(
    VersionExperiment, shorthand="IDELCA"
):
    """Experiment class to build and analyse a project with an
    IDELinearConstantAnalysis."""

    NAME = "PhasarIDELinearConstantAnalysis"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, EmptyReport
        )

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(
            IDELinearConstantAnalysis(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

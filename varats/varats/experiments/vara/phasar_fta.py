"""
Implements the FTA experiment.

The experiment analyses a project with VaRA's feature taint analysis and
generates an EmptyReport.
"""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.reports.empty_report import EmptyReport as EMPTY
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_varats_result_folder,
    PEErrorHandler,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    create_default_compiler_error_handler,
    create_new_success_result_filename,
    create_new_failed_result_filename,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
    get_cached_bc_file_path,
)
from varats.report.report import ReportSpecification


class PhASARFTACheck(actions.Step):  # type: ignore
    """Analyse a project with VaRA and generate the output of the feature taint
    analysis."""

    NAME = "PhASARFTACheck"
    DESCRIPTION = "Generate a full FTA."

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        bc_file_extensions: tp.List[BCFileExtensions],
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__bc_file_extensions = bc_file_extensions
        self.__experiment_handle = experiment_handle

    def analyze(self) -> actions.StepResult:
        """This step performs the actual analysis with the correct flags."""

        project = self.obj

        # Define the output directory.
        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            # Define empty success file
            result_file = create_new_success_result_filename(
                self.__experiment_handle, EMPTY, project, binary
            )

            # Define output file name of failed runs
            error_file = create_new_failed_result_filename(
                self.__experiment_handle, EMPTY, project, binary
            )

            # Combine the input bitcode file's name
            bc_target_file = get_cached_bc_file_path(
                project, binary, self.__bc_file_extensions
            )

            opt_params = [
                "-vara-PFA", "-S",
                str(bc_target_file), "-o", "/dev/null"
            ]

            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            run_cmd = run_cmd > f"{vara_result_folder}/{result_file}"

            # Run the command with custom error handler and timeout
            exec_func_with_pe_error_handler(
                run_cmd,
                PEErrorHandler(vara_result_folder, error_file.filename)
            )


class PhASARTaintAnalysis(VersionExperiment, shorthand="PTA"):
    """Generates a feature taint analysis (FTA) of the project(s) specified in
    the call."""

    NAME = "PhASARFeatureTaintAnalysis"
    REPORT_SPEC = ReportSpecification(EMPTY)

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
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
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        project.cflags += [
            "-O1", "-Xclang", "-disable-llvm-optzns", "-fvara-feature"
        ]

        bc_file_extensions = [
            BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
            BCFileExtensions.FEATURE
        ]

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(
            PhASARFTACheck(project, self.get_handle(), bc_file_extensions)
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

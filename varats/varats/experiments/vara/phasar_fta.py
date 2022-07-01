"""
Implements the FTA experiment.

The experiment analyses a project with VaRA's feature taint analysis and
generates an EmptyReport.
"""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisReport as FAR,
)
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_varats_result_folder,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filename,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
    get_cached_bc_file_path,
)
from varats.provider.feature.feature_model_provider import FeatureModelProvider
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
                self.__experiment_handle, FAR, project, binary
            )

            # Combine the input bitcode file's name
            bc_target_file = get_cached_bc_file_path(
                project, binary, self.__bc_file_extensions
            )

            opt_params = [
                "-vara-PFA",
                "-S",
                "-vara-FAR",
                f"-vara-report-outfile={vara_result_folder}/{result_file}",
                str(bc_target_file),
            ]

            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            # Run the command with custom error handler and timeout
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, FAR,
                    Path(vara_result_folder)
                )
            )


class PhASARTaintAnalysis(VersionExperiment, shorthand="PTA"):
    """Generates a feature taint analysis (FTA) of the project(s) specified in
    the call."""

    NAME = "PhASARFeatureTaintAnalysis"
    REPORT_SPEC = ReportSpecification(FAR)

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

        fm_provider = FeatureModelProvider.get_provider_for_project(project)

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)

        project.cflags += [
            "-O1", "-Xclang", "-disable-llvm-optzns", "-fvara-feature",
            "-fvara-fm-path=" + str(fm_path), "-g"
        ]

        bc_file_extensions = [
            BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
            BCFileExtensions.FEATURE, BCFileExtensions.DEBUG
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

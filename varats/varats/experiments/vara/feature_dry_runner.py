"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import os
from queue import Empty
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import touch
from plumbum import local
from plumbum.commands.base import BoundCommand

from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    ExperimentHandle,
    get_varats_result_folder,
    wrap_unlimit_stack_size,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    VersionExperiment,
    get_default_compile_error_wrapped,
    PEErrorHandler,
)
from varats.experiment.wllvm import (
    get_cached_bc_file_path,
    BCFileExtensions,
    RunWLLVM,
    get_bc_cache_actions,
)
from varats.provider.workload.workload_provider import WorkloadProvider
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.report import FileStatusExtension as FSE
from varats.data.reports.empty_report import EmptyReport


class ExecBinary(actions.Step):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads."""

    NAME = "ExecBinary"
    DESCRIPTION = "Executes each binary without measuring anything."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.run_perf_tracing)
        self.__experiment_handle = experiment_handle

    def run_perf_tracing(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        project: Project = self.obj

        print(f"PWD {os.getcwd()}")

        vara_result_folder = get_varats_result_folder(project)
        workload_provider = WorkloadProvider(project)
        binary: ProjectBinaryWrapper

        for binary in project.binaries:

            if binary.type != BinaryType.EXECUTABLE:
                continue

            # Get result file to use.
            result_file = self.__experiment_handle.get_file_name(
                EmptyReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            # Get workload to use.
            workload = workload_provider.get_workload_parameters(binary)
            if (workload == None):
                print(f"No workload defined for project: {project.name} and binary: {binary.name}. Skipping.")
                continue

            # Execute binary.
            with local.cwd(local.path(project.source_of_primary)):
                
                run_cmd = binary[workload]
                exec_func_with_pe_error_handler(
                    run_cmd,
                    create_default_analysis_failure_handler(
                        self.__experiment_handle, project, EmptyReport,
                        Path(vara_result_folder)
                    )
                )

            # Mark run as successful.
            run_cmd = touch["{res_folder}/{res_file}".format(
                res_folder=vara_result_folder, res_file=result_file
            )]
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, EmptyReport,
                    Path(vara_result_folder)
                )
            )

        return actions.StepResult.OK


class FeatureDryRunner(VersionExperiment, shorthand="FDR"):
    """Test runner for capturing baseline runtime (without any measurements)."""

    NAME = "RunFeatureDry"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project, usdt: bool = False
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add USDT markers, which will remain inactive. 
        if (usdt):
            fm_provider = FeatureModelProvider.create_provider_for_project(project)
            if fm_provider is None:
                raise Exception("Could not get FeatureModelProvider!")

            fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
            if fm_path is None or not fm_path.exists():
                raise FeatureModelNotFound(project, fm_path)

            # Sets FM model flags
            project.cflags += [
                "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"
            ]
            # Sets vara tracing flags
            project.cflags += [
                "-fsanitize=vara",
                "-fvara-instr=usdt"
            ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, EmptyReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(ExecBinary(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class FeaturePerfRunnerUSDT(FeatureDryRunner, shorthand="FDR-USDT"):
    """Test runner for capturing baseline runtime with inactive USDT markers."""

    NAME = "RunDryPerf-USDT"

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        
        return super().actions_for_project(project, True)
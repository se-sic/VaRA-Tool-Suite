"""Module for experiments that measure the runtime overhead introduced by instrumenting
binaries produced by a project."""
import os
from queue import Empty
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time as bbtime
from benchbuild.utils import actions
from benchbuild.utils.cmd import touch, sudo, time, rm
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
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.data.reports.empty_report import EmptyReport
from varats.tools.research_tools.vara import VaRA


class ExecWithTime(actions.Step):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads and with or without
    feature tracing."""

    NAME = "ExecWithTime"
    DESCRIPTION = "Executes each binary and measures its runtime using `time`."

    def __init__(
        self,
        project: Project,
        experiment: VersionExperiment,
        experiment_handle: ExperimentHandle,
        time_reports: TimeReportAggregate,
        usdt: bool = False
    ):
        super().__init__(obj=project, action_fn=self.run_perf_tracing)
        self.__experiment = experiment
        self.__experiment_handle = experiment_handle
        self.__time_reports = time_reports
        self.__usdt = usdt

    def run_perf_tracing(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        project: Project = self.obj

        vara_result_folder = get_varats_result_folder(project)
        workload_provider = WorkloadProvider(project)
        binary: ProjectBinaryWrapper

        for binary in project.binaries:

            if binary.type != BinaryType.EXECUTABLE:
                continue

            # Get workload to use.
            workload = workload_provider.get_workload_parameters(binary)
            if (workload == None):
                print(
                    f"No workload defined for project: {project.name} and binary: {binary.name}. Skipping.")
                continue

            # Execute binary.
            trace_file_path = Path(
                f"/tmp/experiment_{self.__experiment.name}_{binary.name}_trace.json")
            time_report_path = Path(
                f"/tmp/experiment_{self.__experiment.name}_{binary.name}_time_report.txt")
            with local.cwd(local.path(project.source_of_primary)), \
                    local.env(VARA_TRACE_FILE=trace_file_path):

                run_cmd = binary[workload]

                # Attach bpftrace script to activate USDT markers.
                if self.__usdt:
                    # attach bpftrace to binary to allow tracing it via USDT
                    bpftrace_script = Path(VaRA.source_location(
                    ), "vara/tools/perf_bpftrace/UsdtTefMarker.bt")

                    run_cmd = sudo["bpftrace"]["-o", trace_file_path,
                                               "-c", run_cmd,
                                               "-q",
                                               bpftrace_script,
                                               f"{project.source_of_primary}/{binary.path}"]

                run_cmd = time["-v", "-o", time_report_path, run_cmd]

                exec_func_with_pe_error_handler(
                    run_cmd,
                    create_default_analysis_failure_handler(
                        self.__experiment_handle, project, EmptyReport,
                        Path(vara_result_folder)
                    )
                )

                self.__time_reports.add_report(
                    binary.name, TimeReport(time_report_path))

        return actions.StepResult.OK


class WriteTimeReportSummary(actions.Step):  # type: ignore
    """Writes statistics of multiple `TimeReport`s to a result file."""

    NAME = "WriteTimeReportSummary"
    DESCRIPTION = """Writes statistics of multiple executions with `time` to a 
                     result file."""

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        time_reports: TimeReportAggregate
    ):
        super().__init__(obj=project, action_fn=self.write_summary)
        self.__experiment_handle = experiment_handle
        self.__time_reports = time_reports

    def write_summary(self) -> actions.StepResult:
        """Write summary statistics of `TimeReportAggregate` to result file."""
        project: Project = self.obj
        vara_result_folder = get_varats_result_folder(project)

        # Write a result file per binary name.
        for binary_name in self.__time_reports.binary_names():

            result_file = self.__experiment_handle.get_file_name(
                EmptyReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary_name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            self.__time_reports.summary_to_file(binary_name,
                                                f"{vara_result_folder}/{result_file}")

        return actions.StepResult.OK


class FeatureDryTime(VersionExperiment, shorthand="FDT"):
    """Test runner for capturing baseline runtime (without any
    instrumentation)."""

    NAME = "FeatureDryTime"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project, usdt: bool = False, tracing_active: bool = False
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        project.cflags = ["-O3"]

        # Add tracing markers.
        if tracing_active or usdt:
            fm_provider = FeatureModelProvider.create_provider_for_project(
                project)
            if fm_provider is None:
                raise Exception("Could not get FeatureModelProvider!")

            fm_path = fm_provider.get_feature_model_path(
                project.version_of_primary)
            if fm_path is None or not fm_path.exists():
                raise FeatureModelNotFound(project, fm_path)

            # Sets vara tracing flags
            project.cflags += [
                "-fvara-feature",
                f"-fvara-fm-path={fm_path.absolute()}",
                "-fsanitize=vara"
            ]
            if usdt:
                project.cflags += [
                    "-fvara-instr=usdt"
                ]
            elif tracing_active:
                project.cflags += [
                    "-fvara-instr=trace_event"
                ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << bbtime.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, EmptyReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))

        time_reports = TimeReportAggregate()
        for i in range(100):
            analysis_actions.append(ExecWithTime(
                project, self, self.get_handle(), time_reports,
                usdt and tracing_active))

        analysis_actions.append(WriteTimeReportSummary(
            project, self.get_handle(), time_reports))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class FeatureDryTimeUSDT(FeatureDryTime, shorthand="FDTUsdt"):
    """Test runner for capturing baseline runtime with inactive USDT markers."""

    NAME = "FeatureDryTimeUsdt"

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        return super().actions_for_project(project, True, False)


class FeatureTefTime(FeatureDryTime, shorthand="FTT"):
    """Test runner for capturing runtime with TEF markers enabled, which produce
    a Catapult trace file."""

    NAME = "FeatureTefTime"

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        return super().actions_for_project(project, False, True)


class FeatureTefTimeUSDT(FeatureDryTime, shorthand="FTTUsdt"):
    """Test runner for capturing runtime with active USDT markers, which produce
    a Catapult trace file."""

    NAME = "FeatureTefTimeUsdt"

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        return super().actions_for_project(project, True, True)

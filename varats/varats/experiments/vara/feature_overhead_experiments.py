"""Module for experiments that measure the runtime overhead introduced by instrumenting
binaries produced by a project."""
import os
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time as bbtime
from benchbuild.utils import actions
from varats.report.tef_report import TEFReport, TEFReportAggregate
from benchbuild.utils.cmd import time, echo, sh
from plumbum import local
from plumbum.commands.base import BoundCommand

from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    ExperimentHandle,
    get_varats_result_folder,
    create_default_analysis_failure_handler,
    VersionExperiment,
    get_default_compile_error_wrapped,
    PrintProgressStep
)
from varats.provider.workload.workload_provider import WorkloadProvider
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import FileStatusExtension, ReportSpecification
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.data.reports.empty_report import EmptyReport
from varats.tools.research_tools.vara import VaRA


BPFTRACE_SCRIPT_TEMPLATE = "sudo bpftrace -o \"{tef_report_file}\" -q -c " \
    "\"{run_cmd}\" \"{bpftrace_script}\" \"{binary_path}\""


class ExecWithTime(actions.Step):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads and with or without
    feature tracing."""

    NAME = "ExecWithTime"
    DESCRIPTION = "Executes each binary and measures its runtime using `time`."

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        iteration: int,
        usdt: bool = False
    ):
        super().__init__(obj=project, action_fn=self.run_perf_tracing)
        self.__experiment_handle = experiment_handle
        self.__iteration = iteration
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

            # Generate path for TEF report.
            tef_report_dir_name = self.__experiment_handle.get_file_name(
                TEFReportAggregate.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.SUCCESS
            )

            tef_report_dir = Path(
                vara_result_folder, str(tef_report_dir_name))
            tef_report_dir.mkdir(exist_ok=True)

            tef_report_file = Path(
                tef_report_dir, f"tef_iteration_{self.__iteration}.{TEFReport.FILE_TYPE}")

            # Generate path for time report.
            time_report_dir_name = self.__experiment_handle.get_file_name(
                TimeReportAggregate.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.SUCCESS
            )

            time_report_dir = Path(
                vara_result_folder, str(time_report_dir_name))
            time_report_dir.mkdir(exist_ok=True)

            time_report_file = Path(
                time_report_dir, f"time_iteration_{self.__iteration}.{TimeReport.FILE_TYPE}")

            # Execute binary.
            with local.cwd(project.source_of_primary), \
                    local.env(VARA_TRACE_FILE=tef_report_file):

                run_cmd = binary[workload]

                # Attach bpftrace script to activate USDT markers.
                if self.__usdt:
                    # attach bpftrace to binary to allow tracing it via USDT
                    # bpftrace_script = Path(VaRA.install_location(
                    # ), "tools/perf_bpftrace/UsdtTefMarker.bt")

                    bpftrace_script = "/home/jonask/Repos/VaRA/tools_src/vara-llvm-project/vara/tools/perf_bpftrace/UsdtTefMarker.bt"

                    script_text = BPFTRACE_SCRIPT_TEMPLATE.format(
                        tef_report_file=tef_report_file,
                        run_cmd=run_cmd,
                        bpftrace_script=bpftrace_script,
                        binary_path=binary.path
                    )

                    bpftrace_script_path = "/tmp/bpftace_run_script.sh"
                    (echo[script_text] > bpftrace_script_path)()

                    run_cmd = sh[bpftrace_script_path]

                run_cmd = time["-v", "-o", time_report_file, run_cmd]

                exec_func_with_pe_error_handler(
                    run_cmd,
                    create_default_analysis_failure_handler(
                        self.__experiment_handle, project, EmptyReport,
                        Path(vara_result_folder)
                    )
                )

            # Remove report directories if empty.
            if not os.listdir(tef_report_dir):
                tef_report_dir.rmdir()
            if not os.listdir(time_report_dir):
                time_report_dir.rmdir()

        return actions.StepResult.OK


class FeatureDryTime(VersionExperiment, shorthand="FDT"):
    """Test runner for capturing baseline runtime (without any
    instrumentation)."""

    NAME = "FeatureDryTime"

    REPORT_SPEC = ReportSpecification(
        EmptyReport, TimeReportAggregate, TEFReportAggregate)

    def actions_for_project(
        self, project: Project, usdt: bool = False, tracing_active: bool = False
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

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

            project.cflags += ["-flto", "-fuse-ld=lld"]
            project.ldflags += ["-flto"]

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

        num_iterations = 100

        for i in range(num_iterations):

            step = ExecWithTime(
                project, self.get_handle(), i,
                tracing_active and usdt)

            analysis_actions.append(PrintProgressStep(
                project, self, step, i, num_iterations))
            analysis_actions.append(step)

        # print completion of final iteration
        analysis_actions.append(PrintProgressStep(
            project, self, step, num_iterations, num_iterations))

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

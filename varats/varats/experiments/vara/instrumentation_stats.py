"""Module for experiment which measures statistics about the traced execution of
a binary using VaRA's instrumented USDT probes."""
import typing as tp
from pathlib import Path
from time import sleep

from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.extensions import time as bbtime
from benchbuild.utils import actions
from benchbuild.utils.cmd import bpftrace
from plumbum import BG, FG, local
from plumbum.commands.modifiers import Future

from varats.data.reports.usdt_stats_report import VaraInstrumentationStatsReport
from varats.experiment.experiment_util import (
    ExperimentHandle,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
)
from varats.project.project_util import ProjectBinaryWrapper, BinaryType
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.provider.workload.workload_provider import WorkloadProvider
from varats.report.report import FileStatusExtension, ReportSpecification
from varats.tools.research_tools.vara import VaRA


class CaptureInstrumentationStats(actions.Step):  # type: ignore
    """Executes each binary and collects runtime statistics about
    instrumentation using VaRA's USDT probes and a bpftrace script."""

    NAME = "CaptureInstrumentationStats"
    DESCRIPTION = "Executes each binary and collects runtime statistics about" \
        " instrumentation using VaRA's USDT probes and a bpftrace script."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.run)
        self.__experiment_handle = experiment_handle

    def run(self) -> actions.StepResult:
        """Capture instrumentation stats by running the binary with a workload
        and attaching the UsdtExecutionStats.bt."""
        project: Project = self.obj

        vara_result_folder = get_varats_result_folder(project)
        binary: ProjectBinaryWrapper

        for binary in project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            # Get workload to use.
            # TODO (se-sic/VaRA#841): refactor to bb workloads if possible
            workload_provider = WorkloadProvider.create_provider_for_project(
                project
            )
            if not workload_provider:
                print(
                    f"No workload provider for project={project.name}. " \
                    "Skipping."
                )
                return actions.StepResult.CAN_CONTINUE
            workload = workload_provider.get_workload_for_binary(binary.name)
            if workload is None:
                print(
                    f"No workload for project={project.name} " \
                        "binary={binary.name}. Skipping."
                )
                continue

            # Assemble Path for report.
            report_file_name = self.__experiment_handle.get_file_name(
                VaraInstrumentationStatsReport.shorthand(),
                project_name=project.name,
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FileStatusExtension.SUCCESS
            )

            report_file = Path(vara_result_folder, str(report_file_name))

            # Execute binary.
            with local.cwd(project.source_of_primary):
                run_cmd = binary[workload]

                # attach bpftrace to binary to allow tracing it via USDT
                bpftrace_script = Path(
                    VaRA.install_location(),
                    "share/vara/perf_bpf_tracing/UsdtExecutionStats.bt"
                )

                # Assertion: Can be run without sudo password prompt. To
                # guarentee this, add an entry to /etc/sudoers.
                bpftrace_cmd = bpftrace["-o", report_file, bpftrace_script,
                                        binary.path]

                bpftrace_runner: Future
                with local.as_root():
                    bpftrace_runner = bpftrace_cmd & BG

                sleep(3)  # give bpftrace time to start up

                # Run.
                run_cmd & FG  # pylint: disable=W0104

                # Wait for bpftrace running in background to exit.
                bpftrace_runner.wait()

        return actions.StepResult.OK


class InstrumentationStatsRunner(VersionExperiment, shorthand="IS"):
    """Runner for measuring statistics about the traced execution of a binary
    using VaRA's instrumented USDT probes."""

    NAME = "VaraIS"

    REPORT_SPEC = ReportSpecification(VaraInstrumentationStatsReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add tracing markers.
        fm_provider = FeatureModelProvider.create_provider_for_project(project)
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)

        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # Sets vara tracing flags
        project.cflags += [
            "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}",
            "-fsanitize=vara", "-fvara-instr=usdt", "-flto", "-fuse-ld=lld"
        ]

        project.ldflags += ["-flto"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << bbtime.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, VaraInstrumentationStatsReport
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))

        analysis_actions.append(
            CaptureInstrumentationStats(project, self.get_handle())
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

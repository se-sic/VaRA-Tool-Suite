"""Implements an experiment for VaRA's UsdtExecutionStats.bt, which collects
execution statistics about the events produced during tracing using USDT probes
and eBPF."""

import typing as tp
from pathlib import Path
from time import sleep

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.cmd import bpftrace, sudo
from plumbum import BG
from plumbum.commands.modifiers import Future

from varats.data.reports.feature_tracing_stats_report import (
    FeatureTracingStatsReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    create_new_success_result_filepath,
)
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.tools.research_tools.vara import VaRA


class CaptureTracingStats(actions.ProjectStep):  # type: ignore
    """
    Step to collect execution statistics about the events produced during
    tracing using USDT probes and VaRA's UsdtExecutionStats.bt bpftrace script.

    IMPORTANT: Attaching eBPF tracing programs requires root privileges, make
    sure that bpftrace can be invoked with sudo without having to enter the
    passwort first. This can be achieved by adding a file to
    `/etc/sudoers.d/`.
    """

    NAME = "CaptureTracingStats"
    DESCRIPTION = "Capture feature tracing event statistics"

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            # get workload to use
            workloads = workload_commands(
                self.project, binary, [WorkloadCategory.MEDIUM]
            )
            if len(workloads) == 0:
                print(
                    f"No workload for project={self.project.name} "
                    f"binary={binary.name}. Skipping."
                )
                continue
            if len(workloads) > 1:
                raise RuntimeError(
                    "Currently, only a single workload is supported. "
                    f"project={self.project.name} binary={binary.name}"
                )
            workload = workloads[0]

            # report path
            stats_report = create_new_success_result_filepath(
                self.__experiment_handle, FeatureTracingStatsReport,
                self.project, binary
            )

            # attach bpftrace script
            bpftrace_script = Path(
                VaRA.install_location(),
                "share/vara/perf_bpf_tracing/UsdtExecutionStats.bt"
            )

            # assertion: Can be run without sudo password prompt
            bpftrace_cmd = bpftrace["-f", "json", "-o", stats_report,
                                    bpftrace_script,
                                    self.project.source_of_primary /
                                    binary.path]
            bpftrace_cmd = sudo[bpftrace_cmd]
            bpftrace_runner: Future = bpftrace_cmd & BG
            sleep(3)  # give bpftrace time to start up

            # execute binary with workload
            run_cmd = workload.command.as_plumbum(project=self.project)
            with cleanup(workload):
                bb.watch(run_cmd)()

            # Wait for bpftrace running in background to exit.
            bpftrace_runner.wait()

        return actions.StepResult.OK


class FeatureTracingStats(FeatureExperiment, shorthand="FTS"):
    """Collect execution statistics about the events produced during tracing
    using USDT probes and VaRA's UsdtExecutionStats.bt bpftrace script."""

    NAME = "FeatureTracingStats"

    REPORT_SPEC = ReportSpecification(FeatureTracingStatsReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        return self.get_common_tracing_actions(
            project,
            FeatureInstrType.USDT,
            [CaptureTracingStats(project, self.get_handle())],
            instruction_threshold=0
        )

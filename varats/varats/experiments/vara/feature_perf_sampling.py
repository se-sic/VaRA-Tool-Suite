"""Experiments for sampling feature performance by translating perf call stack
samples using location information of VaRA's instrumented raw USDT probes."""

import typing as tp
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.utils.actions import ProjectStep, Step, StepResult
from benchbuild.utils.cmd import time, cp, mkdir, perf
from plumbum import local

from varats.data.reports.perf_profile_report import (
    PerfProfileReport,
    PerfProfileReportAggregate,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    ZippedReportFolder,
    get_varats_result_folder,
    create_new_success_result_filepath,
)
from varats.experiment.workload_util import workload_commands, WorkloadCategory
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import ReportSpecification


class SampleWithPerfAndTime(ProjectStep):  # type: ignore
    """See `DESCRIPTION`."""

    NAME = "SampleWithPerfAndTime"
    DESCRIPTION = """Sample call stack with perf and measure total execution
                  using GNU Time. Additionally, compiled binaries are copied to
                  the results directory for further investigation afterwards.

                  Each binary is executed `num_iterations` times. A
                  `TimeReportAggregate` and `PerfProfileReportAggregate` are
                  produced for each binary, which contains the respective
                  information from each iteration."""

    project: VProject

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
        sampling_rate: int = 997,
        num_iterations: int = 2
    ):
        super().__init__(project=project)
        self.experiment_handle = experiment_handle
        self.sampling_rate = sampling_rate
        self.num_iterations = num_iterations

    def __call__(self) -> StepResult:
        vara_results_dir = get_varats_result_folder(self.project)
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            # copy binary to allow investigation of instrumentation
            binaries_dir = vara_results_dir / "compiled_binaries"
            mkdir("-p", binaries_dir)
            print(
                "source_of_primary:",
                self.project.source_of_primary,
                flush=True
            )
            cp(
                Path(self.project.source_of_primary,
                     binary.path), binaries_dir /
                (f"{binary.name}_" + self.experiment_handle.shorthand())
            )

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

            # report paths
            perf_report_agg = create_new_success_result_filepath(
                self.experiment_handle, PerfProfileReportAggregate,
                self.project, binary
            )
            time_report_agg = create_new_success_result_filepath(
                self.experiment_handle, TimeReportAggregate, self.project,
                binary
            )

            with ZippedReportFolder(
                time_report_agg.full_path()
            ) as time_report_agg_dir, ZippedReportFolder(
                perf_report_agg.full_path()
            ) as perf_report_agg_dir, local.cwd(self.project.builddir):
                for i in range(self.num_iterations):
                    print(
                        f"Binary={binary.name} Progress "
                        f"{i}/{self.num_iterations}",
                        flush=True
                    )

                    time_report_file = Path(
                        time_report_agg_dir,
                        f"iteration_{i}.{TimeReport.FILE_TYPE}"
                    )
                    perf_report_file = Path(
                        perf_report_agg_dir,
                        f"iteration_{i}.{PerfProfileReport.FILE_TYPE}"
                    )

                    run_cmd = workload.command.as_plumbum(project=self.project)
                    run_cmd = time["-v", "-o", time_report_file, run_cmd]
                    run_cmd = perf["record", "-F", self.sampling_rate, "-g",
                                   "--user-callchains", "-o", perf_report_file,
                                   run_cmd]

                    with cleanup(workload):
                        run_cmd()
        return StepResult.OK


class TranslateCallStackSamples(ProjectStep):  # type: ignore
    """See `DESCRIPTION`."""

    NAME = "TranslateCallStackSamples"
    DESCRIPTION = """Translate the collected call stack samples into feature
                  region stack samples using the locations of USDT raw probes
                  instrumented at entry and exit locations of feature
                  regions."""

    project: VProject

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.experiment_handle = experiment_handle

    def __call__(self) -> StepResult:
        # TODO (Jonas Kaufmann) implement this
        return StepResult.OK


class FeaturePerfSampling97Hz(FeatureExperiment, shorthand="FPS97Hz"):
    """Sample feature performance using a sampling frequency of 97 Hz and
    measure total execution time."""

    NAME = "FeaturePerfSampling97Hz"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, PerfProfileReportAggregate
    )

    def actions_for_project(
        self,
        project: VProject,
    ) -> tp.MutableSequence[Step]:
        return self.get_common_tracing_actions(
            project,
            FeatureInstrType.USDT_RAW,
            [SampleWithPerfAndTime(project, self.get_handle(), 97)],
            instruction_threshold=0
        )


class FeaturePerfSampling997Hz(FeatureExperiment, shorthand="FPS997Hz"):
    """Sample feature performance using a sampling frequency of 997 Hz and
    measure total execution time."""

    NAME = "FeaturePerfSampling997Hz"
    REPORT_SPEC = ReportSpecification(
        TimeReportAggregate, PerfProfileReportAggregate
    )

    def actions_for_project(
        self,
        project: VProject,
    ) -> tp.MutableSequence[Step]:
        return self.get_common_tracing_actions(
            project,
            FeatureInstrType.USDT_RAW,
            [SampleWithPerfAndTime(project, self.get_handle(), 997)],
            instruction_threshold=0
        )

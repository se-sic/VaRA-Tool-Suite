"""Implements an experiment that profiles the execution of a project binary."""

import importlib.resources as resources
import typing as tp

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.actions import ProjectStep, StepResult
from benchbuild.utils.cmd import perf, time
from plumbum import local

from varats.data.reports.perf_profile_report import (
    WLPerfProfileReportAggregate,
    PerfProfileReport,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    ZippedReportFolder,
    create_new_success_result_filepath,
    ExperimentHandle,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import WLTimeReportAggregate, TimeReport
from varats.report.report import ReportSpecification


class SampleWithPerfAndTime(ProjectStep):  # type: ignore
    """Step to sample call stack with perf and measure total execution using GNU
    Time."""

    NAME = "SampleWithPerfAndTime"
    DESCRIPTION = (
        "Sample call stack using perf and measure total execution time"
    )

    project: VProject

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
        binary: ProjectBinaryWrapper,
        sampling_rate: int = 997
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__binary = binary
        self.__sampling_rate = sampling_rate

    def __call__(self) -> StepResult:
        # get workload to use
        workloads = workload_commands(
            self.project, self.__binary, [WorkloadCategory.MEDIUM]
        )
        if len(workloads) == 0:
            print(
                f"No workload for project={self.project.name} "
                f"binary={self.__binary.name}. Skipping."
            )
            return StepResult.OK

        # report paths
        perf_report_agg = create_new_success_result_filepath(
            self.__experiment_handle, WLPerfProfileReportAggregate,
            self.project, self.__binary
        )
        time_report_agg = create_new_success_result_filepath(
            self.__experiment_handle, WLTimeReportAggregate, self.project,
            self.__binary
        )

        with ZippedReportFolder(
            time_report_agg.full_path()
        ) as time_report_agg_dir, ZippedReportFolder(
            perf_report_agg.full_path()
        ) as perf_report_agg_dir, local.cwd(self.project.builddir):
            for workload in workloads:
                time_report_file = \
                    time_report_agg_dir / create_workload_specific_filename(
                        "time_report", workload.command, file_suffix=TimeReport.FILE_TYPE)
                perf_report_file = \
                    perf_report_agg_dir / create_workload_specific_filename(
                        "time_report", workload.command, file_suffix=PerfProfileReport.FILE_TYPE)

                run_cmd = workload.command.as_plumbum(project=self.project)
                run_cmd = time["-v", "-o", time_report_file, run_cmd]
                run_cmd = perf["record", "-F", self.__sampling_rate, "-g",
                               "--user-callchains", "-o", perf_report_file,
                               run_cmd]

                with cleanup(workload):
                    bb.watch(run_cmd)(retcode=None)

                    perf_script_source = resources.files("varats").joinpath(
                        "resources/perf_script_overhead_calculation.py"
                    )
                    with resources.as_file(perf_script_source) as perf_script:
                        bb.watch(
                            perf["script", "-s", perf_script, "-i",
                                 perf_report_file]
                        )()

        return StepResult.OK


class PerfSampling(VersionExperiment, shorthand="PS"):
    """Generates perf sampling files."""

    NAME = "PerfSampling"

    REPORT_SPEC = ReportSpecification(
        WLTimeReportAggregate, WLPerfProfileReportAggregate
    )

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        project.runtime_extension = run.RuntimeExtension(project, self)
        project.compiler_extension = compiler.RunCompiler(project, self
                                                         ) << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        # Only consider the main/first binary
        binary = project.binaries[0]

        analysis_actions = [
            actions.Compile(project),
            SampleWithPerfAndTime(project, self.get_handle(), binary, 997),
            actions.Clean(project)
        ]

        return analysis_actions

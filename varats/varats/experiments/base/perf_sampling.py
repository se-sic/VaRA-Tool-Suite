"""Implements an experiment that profiles the execution of a project binary."""

import importlib.resources as resources
import typing as tp

import benchbuild as bb
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.actions import ProjectStep, StepResult
from benchbuild.utils.cmd import perf, time
from plumbum import local, ProcessExecutionError

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
from varats.experiments.base.precompile import RestoreBinaries, PreCompile
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import WLTimeReportAggregate, TimeReport
from varats.report.function_overhead_report import WLFunctionOverheadReportAggregate, FunctionOverheadReport
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


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
        repetitions: int = 1,
        sampling_rate: int = 997
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__binary = binary
        self.__repetitions = repetitions
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

        # check if perf record works
        try:
            perf["record", "-o", "/dev/null", "ls"]
        except ProcessExecutionError:
            return StepResult.ERROR

        # report paths
        perf_report_agg = create_new_success_result_filepath(
            self.__experiment_handle, WLFunctionOverheadReportAggregate,
            self.project, self.__binary, get_current_config_id(self.project)
        )
        time_report_agg = create_new_success_result_filepath(
            self.__experiment_handle, WLTimeReportAggregate, self.project,
            self.__binary, get_current_config_id(self.project)
        )

        with ZippedReportFolder(
            time_report_agg.full_path()
        ) as time_report_agg_dir, ZippedReportFolder(
            perf_report_agg.full_path()
        ) as perf_report_agg_dir, local.cwd(self.project.builddir):
            for workload in workloads:
                for repetition in range(self.__repetitions):
                    time_report_file = \
                        time_report_agg_dir / create_workload_specific_filename(
                        "time_report", workload.command, repetition,
                        TimeReport.FILE_TYPE
                    )
                    overhead_report_file = \
                        perf_report_agg_dir / create_workload_specific_filename(
                        "overhead_report", workload.command, repetition,
                        FunctionOverheadReport.FILE_TYPE
                    )
                    perf_data_file = \
                        f"perf_{workload.command.label}_{repetition}.data"

                    run_cmd = workload.command.as_plumbum(project=self.project)
                    run_cmd = time["-v", "-o", f'{time_report_file}', run_cmd.formulate()]
                    run_cmd = perf["record", "-F", self.__sampling_rate, "-g",
                                   "--user-callchains", "-o", str(perf_data_file),
                                   run_cmd.formulate()]

                    with cleanup(workload):
                        bb.watch(run_cmd)(retcode=None)
                        perf_script_source = resources.files("varats").joinpath(
                            "resources"
                        ).joinpath("perf_script_overhead_calculation.py")
                        with resources.as_file(
                            perf_script_source
                        ) as perf_script:
                            perf_script_cmd = perf["script", "-s", perf_script,
                                                   "-i", perf_data_file]
                            (perf_script_cmd > str(overhead_report_file))()

        return StepResult.OK


class PerfSampling(VersionExperiment, shorthand="PS"):
    """Generates perf sampling files."""

    NAME = "PerfSampling"

    REPORT_SPEC = ReportSpecification(
        WLTimeReportAggregate, WLFunctionOverheadReportAggregate
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
            RestoreBinaries(project, PreCompile),
            SampleWithPerfAndTime(project, self.get_handle(), binary, 10, 997),
            actions.Clean(project)
        ]

        return analysis_actions

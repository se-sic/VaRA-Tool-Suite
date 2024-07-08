"""Implements an experiment that profiles the execution of a project binary."""

import typing as tp
from importlib import resources
from pathlib import Path

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
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiment.wllvm import RunWLLVM
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.experiments.base.precompile import RestoreBinaries, PreCompile
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.function_overhead_report import (
    FunctionOverheadReport,
    WLFunctionOverheadReportAggregate,
    MPRWLFunctionOverheadReportAggregate,
)
from varats.report.gnu_time_report import (
    TimeReport,
    WLTimeReportAggregate,
    MPRWLTimeReportAggregate,
)
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash

if tp.TYPE_CHECKING:
    from benchbuild.command import ProjectCommand

    from varats.project.project_util import ProjectBinaryWrapper
    from varats.project.varats_project import VProject
    from varats.report.report import BaseReport, ReportFilepath


def _sample_with_perf_and_time(
    project: "VProject", perf_report_agg: Path, time_report_agg: Path,
    workloads: tp.List["ProjectCommand"], repetitions: int, sampling_rate: int
) -> None:
    with ZippedReportFolder(time_report_agg
                           ) as time_report_agg_dir, ZippedReportFolder(
                               perf_report_agg
                           ) as perf_report_agg_dir:
        for workload in workloads:
            for repetition in range(repetitions):
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

                run_cmd = workload.command.as_plumbum(project=project)
                run_cmd = time["-v", "-o", f'{time_report_file}',
                               run_cmd.formulate()]
                run_cmd = perf["record", "-F", sampling_rate, "-g",
                               "--user-callchains", "-o",
                               str(perf_data_file),
                               run_cmd.formulate()]

                with cleanup(workload):
                    bb.watch(run_cmd)(retcode=None)
                    perf_script_source = resources.files("varats").joinpath(
                        "resources"
                    ).joinpath("perf_script_overhead_calculation.py")
                    with resources.as_file(perf_script_source) as perf_script:
                        perf_script_cmd = perf["script", "-s", perf_script,
                                               "-i", perf_data_file]
                        (perf_script_cmd > str(overhead_report_file))()


class SampleWithPerfAndTime(ProjectStep):  # type: ignore
    """Step to sample call stack with perf and measure total execution using GNU
    Time."""

    NAME = "SampleWithPerfAndTime"
    DESCRIPTION = (
        "Sample call stack using perf and measure total execution time"
    )

    project: "VProject"

    def __init__(
        self,
        project: "VProject",
        experiment_handle: ExperimentHandle,
        binary: "ProjectBinaryWrapper",
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

        with local.cwd(self.project.builddir):
            _sample_with_perf_and_time(
                self.project, perf_report_agg.full_path(),
                time_report_agg.full_path(), workloads, self.__repetitions,
                self.__sampling_rate
            )

        return StepResult.OK


class SampleWithPerfAndTimeSynth(OutputFolderStep):
    """Step to sample call stack with perf and measure total execution using GNU
    Time."""

    NAME = "SampleWithPerfAndTimeSynth"
    DESCRIPTION = (
        "Sample call stack using perf and measure total execution time"
    )

    project: "VProject"

    def __init__(
        self,
        project: "VProject",
        binary: "ProjectBinaryWrapper",
        perf_report_filename: Path,
        time_report_filename: Path,
        repetitions: int = 1,
        sampling_rate: int = 997
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__perf_report_filename = perf_report_filename
        self.__time_report_filename = time_report_filename
        self.__repetitions = repetitions
        self.__sampling_rate = sampling_rate

    def call_with_output_folders(
        self, tmp_dirs: tp.Dict[tp.Type["BaseReport"], Path]
    ) -> StepResult:
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
        perf_report_agg = tmp_dirs[MPRWLFunctionOverheadReportAggregate
                                  ] / self.__perf_report_filename
        time_report_agg = tmp_dirs[MPRWLTimeReportAggregate
                                  ] / self.__time_report_filename

        with local.cwd(self.project.builddir):
            _sample_with_perf_and_time(
                self.project, perf_report_agg, time_report_agg, workloads,
                self.__repetitions, self.__sampling_rate
            )

        return StepResult.OK


class PerfSampling(VersionExperiment, shorthand="PS"):
    """Generates perf sampling files."""

    NAME = "PerfSampling"

    REPORT_SPEC = ReportSpecification(
        WLTimeReportAggregate, WLFunctionOverheadReportAggregate
    )

    def actions_for_project(
        self, project: "VProject"
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


class TimeWorkloadsSynth(VersionExperiment, shorthand="PSS"):
    """Generates perf sampling files for synthetic case studies."""

    NAME = "PerfSamplingSynth"

    REPORT_SPEC = ReportSpecification(
        MPRWLTimeReportAggregate, MPRWLFunctionOverheadReportAggregate
    )

    def actions_for_project(
        self, project: "VProject"
    ) -> tp.MutableSequence[actions.Step]:
        """"""
        project.runtime_extension = run.RuntimeExtension(project, self)
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << RunWLLVM() \
                                     << run.WithTimeout()

        config_id = get_current_config_id(project)
        # Only consider the main/first binary
        binary = project.binaries[0]

        patch_provider = PatchProvider.get_provider_for_project(project)
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )
        regression_patches = patches["regression"]

        repetitions = 10

        analysis_actions = [actions.Compile(project)]

        patch_steps = [
            SampleWithPerfAndTimeSynth(
                project,
                binary,
                Path(
                    MPRWLFunctionOverheadReportAggregate.
                    create_baseline_report_name("overhead_reports")
                ),
                Path(
                    MPRWLTimeReportAggregate.
                    create_baseline_report_name("time_reports")
                ),
                repetitions,
                997,
            )
        ]

        for patch in regression_patches:
            patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                SampleWithPerfAndTimeSynth(
                    project, binary,
                    Path(
                        MPRWLFunctionOverheadReportAggregate.
                        create_patched_report_name(patch, "overhead_reports")
                    ),
                    Path(
                        MPRWLTimeReportAggregate.create_patched_report_name(
                            patch, "time_reports"
                        )
                    ), repetitions, 997
                )
            )
            patch_steps.append(RevertPatch(project, patch))

        result_filepaths: tp.Dict[tp.Type["BaseReport"], "ReportFilepath"] = {
            MPRWLFunctionOverheadReportAggregate:
                create_new_success_result_filepath(
                    self.get_handle(), MPRWLFunctionOverheadReportAggregate,
                    project, binary, config_id
                ),
            MPRWLTimeReportAggregate:
                create_new_success_result_filepath(
                    self.get_handle(), MPRWLTimeReportAggregate, project,
                    binary, config_id
                )
        }

        analysis_actions.append(
            ZippedExperimentSteps(result_filepaths, patch_steps)
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

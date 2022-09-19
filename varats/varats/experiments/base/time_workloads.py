"""Implements an experiment times the execution of all project binaries."""

import itertools
import typing as tp
from pathlib import Path

import benchbuild.extensions.time as bb_time
from benchbuild import Project
from benchbuild.command import ProjectCommand, unwrap, enable_rollback
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import touch, time, wget, rm, ls
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
    get_varats_result_folder,
    ZippedReportFolder,
    ZippedExperimentSteps,
)
from varats.experiment.wllvm import RunWLLVM
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import ReportSpecification


class TimeProjectWorkloads(actions.ProjectStep):  # type: ignore
    """Times the execution of all project workloads."""

    NAME = "TimeWorkloads"
    DESCRIPTION = "Time the execution of all project workloads."

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle, num: int
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__num = num

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Only create a report file."""
        self.project: VProject

        with local.cwd(self.project.builddir):
            for prj_command in workload_commands(
                self.project, WorkloadCategory.SMALL, WorkloadCategory.MEDIUM
            ):
                pb_cmd = prj_command.command.as_plumbum(project=self.project)
                print(f"{pb_cmd}")

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "time_report", prj_command.command, self.__num, ".txt"
                )

                run_cmd = time['-v', '-o', f'{run_report_name}', pb_cmd]

                with enable_rollback(prj_command):
                    print(f"{run_cmd=}")
                    run_cmd()

        return actions.StepResult.OK


class TimeWorkloads(VersionExperiment, shorthand="TWL"):
    """Generates time report files."""

    NAME = "TimeWorkloads"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        measurment_repetitions = 2
        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            # TODO: handle binary name. token?
            self.get_handle().report_spec().main_report,
            project,
            project.binaries[0]
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))

        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    TimeProjectWorkloads(project, self.get_handle(), rep_num)
                    for rep_num in range(0, measurment_repetitions)
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

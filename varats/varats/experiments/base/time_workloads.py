"""Implements an experiment that times the execution of all project binaries."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import time
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import ReportSpecification


class TimeProjectWorkloads(actions.ProjectStep):  # type: ignore
    """Times the execution of all project example workloads."""

    NAME = "TimeWorkloads"
    DESCRIPTION = "Time the execution of all project example workloads."

    project: VProject

    def __init__(
        self, project: Project, num: int, binary: ProjectBinaryWrapper
    ):
        super().__init__(project=project)
        self.__num = num
        self.__binary = binary

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Only create a report file."""

        with local.cwd(self.project.builddir):
            for prj_command in workload_commands(
                self.project, self.__binary, [WorkloadCategory.EXAMPLE]
            ):
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "time_report", prj_command.command, self.__num, ".txt"
                )

                run_cmd = time['-v', '-o', f'{run_report_name}', pb_cmd]

                with cleanup(prj_command):
                    run_cmd()

        return actions.StepResult.OK


class TimeWorkloads(VersionExperiment, shorthand="TWL"):
    """Generates time report files."""

    NAME = "TimeWorkloads"

    REPORT_SPEC = ReportSpecification(TimeReportAggregate)

    def actions_for_project(
        self, project: VProject
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

        # Only consider the main/first binary
        binary = project.binaries[0]

        measurement_repetitions = 2
        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))

        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    TimeProjectWorkloads(project, rep_num, binary)
                    for rep_num in range(0, measurement_repetitions)
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""Implements an experiment that times the execution of all project binaries."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.command import cleanup
from benchbuild.extensions import run
from benchbuild.utils import actions
from benchbuild.utils.cmd import time
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.experiments.base.precompile import RestoreBinaries
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class TimeProjectWorkloads(OutputFolderStep):
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

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Only create a report file."""

        with local.cwd(self.project.builddir):
            for prj_command in workload_commands(
                self.project, self.__binary, [WorkloadCategory.MEDIUM]
            ):
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "time_report", prj_command.command, self.__num, ".txt"
                )

                run_cmd = time['-v', '-o', f'{run_report_name}', pb_cmd]

                with cleanup(prj_command):
                    run_cmd(retcode=None)

        return actions.StepResult.OK


class TimeWorkloads(VersionExperiment, shorthand="TWL"):
    """
    Generates time report files.

    To avoid the overhead of repeatedly compiling the project, this experiment
    uses precompiled binaries as generated by the PreCompile experiment.
    Therefore, you should run the PreCompile experiment before running this.
    """

    NAME = "TimeWorkloads"

    REPORT_SPEC = ReportSpecification(WLTimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Only consider the main/first binary
        binary = project.binaries[0]

        measurement_repetitions = 5

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        analysis_actions = [
            # use precompiled binaries
            RestoreBinaries(project, self.get_handle()),
            ZippedExperimentSteps(
                result_filepath, [
                    TimeProjectWorkloads(project, rep_num, binary)
                    for rep_num in range(0, measurement_repetitions)
                ]
            ),
            actions.Clean(project)
        ]

        return analysis_actions

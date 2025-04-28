"""Implements an experiment that times the execution of all project binaries."""

import json
import re
import typing as tp
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import perf
from plumbum import local

from varats.data.reports.perf_stat_report import PerfStatReportAggregate
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


def fix_json_format(file_path: Path) -> None:
    """Correcting wrong json format."""
    wrong_decimal_regex = r'"?(\d+),(\d+)"?'
    fixed_data = []

    with open(file_path, "r") as file:
        for line in file:
            fixed_line = re.sub(wrong_decimal_regex, r"\1.\2", line)
            try:
                json_obj = json.loads(fixed_line)
                fixed_data.append(json_obj)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e} in line: {fixed_line}")
                continue

    with open(file_path, "w") as file:
        json.dump(fixed_data, file)


class PerfStat(OutputFolderStep):
    """Times the execution of all project example workloads."""

    NAME = "PerfStat"
    DESCRIPTION = "Perf stat measurement for projects."

    project: VProject

    METRICS = ["CPU_Utilization", "DRAM_BW_Use", "L1MPKI", "L2MPKI", "L3MPKI"]

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
                self.project, self.__binary,
                [WorkloadCategory.EXAMPLE, WorkloadCategory.MEDIUM]
            ):
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                run_report_name = tmp_dir / create_workload_specific_filename(
                    "perf_stat", prj_command.command, self.__num, ".json"
                )

                run_cmd = perf['stat', '-I 1', '-j', '-o'
                               f'{run_report_name}', pb_cmd]

                with cleanup(prj_command):
                    run_cmd()

                fix_json_format(run_report_name)

        return actions.StepResult.OK


class PerfStatExperiment(VersionExperiment, shorthand="PSE"):
    """Generates time report files."""

    NAME = "PerfStat"

    REPORT_SPEC = ReportSpecification(PerfStatReportAggregate)

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
            self.get_handle().report_spec().main_report,
            project,
            binary,
            config_id=get_current_config_id(project),
        )

        analysis_actions = [
            actions.Compile(project),
            ZippedExperimentSteps(
                result_filepath, [
                    PerfStat(project, rep_num, binary)
                    for rep_num in range(0, measurement_repetitions)
                ]
            ),
            actions.Clean(project)
        ]

        return analysis_actions

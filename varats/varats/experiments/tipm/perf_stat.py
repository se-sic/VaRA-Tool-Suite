"""Implements an experiment that times the execution of all project binaries."""

import json
import re
import typing as tp
from pathlib import Path

import benchbuild
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import ProjectStep
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

INTERVAL = 50


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
                #print(f"Failed to decode JSON: {e} in line: {fixed_line}")
                continue

    with open(file_path, "w") as file:
        json.dump(fixed_data, file)


class PerfStat(OutputFolderStep):
    """Times the execution of all project example workloads."""

    NAME = "PerfStat"
    DESCRIPTION = "Perf stat measurement for projects."

    project: VProject

    # TODO: Maybe we want to make this a bit more flexible by reading these from
    # a text file or a the varats config?
    METRICS = [
        "branch_misprediction_ratio",
        "all_l2_cache_hits",
        "all_l2_cache_misses",
        "ic_fetch_miss_ratio",
        "op_cache_fetch_miss_ratio",
        "all_l2_cache_accesses",
    ]
    EVENTS = [
        "branch-misses", "branches", "l3_cache_accesses", "l3_misses",
        "L1-dcache-loads", "L1-dcache-load-misses",
        "l2_request_g1.all_no_prefetch"
    ]

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
                self.project, self.__binary, [
                    WorkloadCategory.EXAMPLE, WorkloadCategory.SMALL,
                    WorkloadCategory.MEDIUM
                ]
            ):
                run_report_name = tmp_dir / create_workload_specific_filename(
                    "perf_stat", prj_command.command, self.__num, ".json"
                )

                perf_cmd = perf['stat', f'-I {INTERVAL}', '-j',
                                f"--metrics={','.join(self.METRICS)}",
                                f"--event={','.join(self.EVENTS)}", '-o',
                                f'{run_report_name}']

                with cleanup(prj_command):
                    run_cmd = prj_command.command.as_plumbum_wrapped_with(
                        perf_cmd, project=self.project
                    )
                    #benchbuild.watch(run_cmd)()
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

        analysis_actions: tp.List[ProjectStep | ZippedExperimentSteps] = [
            actions.Compile(project)
        ]
        measurement_repetitions = 1
        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report,
                project,
                binary,
                config_id=get_current_config_id(project),
            )

            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath, [
                        PerfStat(project, rep_num, binary)
                        for rep_num in range(0, measurement_repetitions)
                    ]
                )
            )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

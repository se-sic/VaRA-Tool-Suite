"""Implements an experiment times the execution of all project binaries."""

import typing as tp
from pathlib import Path

import benchbuild.extensions.time as bb_time
from benchbuild import Project
from benchbuild.extensions import compiler, run
from benchbuild.utils import actions
from benchbuild.utils.cmd import touch, time, wget, rm
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    get_varats_result_folder,
    create_new_success_result_filename,
    ZippedReportFolder,
)
from varats.experiment.wllvm import RunWLLVM
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import ReportSpecification


# Please take care when changing this file, see docs experiments/just_compile
class TimeProjectWorkloads(actions.Step):  # type: ignore
    """Times the execution time of all project workloads."""

    NAME = "TimeAnalysis"
    DESCRIPTION = "Time the execution of all produced binaries."

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle

    def analyze(self) -> actions.StepResult:
        """Only create a report file."""
        project = self.obj
        repetitions = 10

        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            result_file = create_new_success_result_filename(
                self.__experiment_handle,
                self.__experiment_handle.report_spec().main_report, project,
                binary
            )

            report_file = f"{vara_result_folder}/{result_file}"

            with local.cwd(local.path(project.source_of_primary)):
                workload = "countries-land-1km.geo.json"

                with ZippedReportFolder(Path(report_file)) as time_reports_dir:
                    for i in range(repetitions):
                        wget(
                            "https://github.com/simonepri/geo-maps/releases/"
                            "download/v0.6.0/countries-land-1km.geo.json", "-O",
                            workload
                        )

                        run_report_name = Path(
                            time_reports_dir
                        ) / f"time_report_{i}.txt"

                        rm('-f', workload + ".xz")
                        rm('-f', workload + ".lrz")
                        rm('-f', workload + ".gz")

                        run_cmd = time['-v', '-o', f'{run_report_name}',
                                       binary[workload]]

                        print(f"Run-{i}: ({run_cmd})")

                        exec_func_with_pe_error_handler(
                            run_cmd,
                            create_default_analysis_failure_handler(
                                self.__experiment_handle, project,
                                self.__experiment_handle.report_spec().
                                main_report, Path(vara_result_folder)
                            )
                        )

        return actions.StepResult.OK


# Please take care when changing this file, see docs experiments/just_compile
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
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << bb_time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            TimeProjectWorkloads(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

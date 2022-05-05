"""Implements an empty experiment that just compiles the project."""
import os.path
import tempfile
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import rm
from benchbuild.utils.cmd import mkdir, touch, time
from plumbum import local
from plumbum.cmd import rm, ls

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    get_varats_result_folder, ZippedReportFolder,
)
from varats.experiment.wllvm import RunWLLVM
from varats.report.gnu_time_report import TimeReport, TimeReportAggregate
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification


class xzBlackboxAnalysis(actions.Step):  # type: ignore
    """Empty analysis step for testing."""

    NAME = "xzBlackboxAnalysis"
    DESCRIPTION = "Runs xz as a blackbox."
    compressionLevel = 0

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        compressionLvl
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__experiment_handle = experiment_handle
        self.compressionLevel = compressionLvl

    def analyze(self) -> actions.StepResult:
        """Only create a report file."""
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj
        vara_result_folder = get_varats_result_folder(project)

        for binary in project.binaries:
            result_file = self.__experiment_handle.get_file_name(
                self.__experiment_handle.report_spec().main_report.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS,
            )

            file_path = "/scratch/messerig/varaEnv/experimentFiles/countries-land-1m.geo.json"
            xz_params = [
                "-{compression}".format(compression=self.compressionLevel),
                "-k", file_path
            ]
            file_path_xz = "/scratch/messerig/varaEnv/experimentFiles/countries-land-1m.geo.json.xz"

            number_of_repetition = 3

            with local.cwd(local.path(project.source_of_primary)):
                xz_cmd = binary[xz_params]
                rm_cmd = rm[file_path_xz]

                with ZippedReportFolder(vara_result_folder / result_file.filename) as time_reports_dir:
                    for i in range(number_of_repetition):
                        time_xz_cmd = time["-v", "-o",
                                           Path(time_reports_dir) / f"time_report_{i}.txt",
                                           xz_cmd]
                        rm_cmd()
                        exec_func_with_pe_error_handler(
                            time_xz_cmd,
                            create_default_analysis_failure_handler(
                                self.__experiment_handle, project,
                                self.__experiment_handle.report_spec().main_report,
                                Path(time_reports_dir),
                            )
                        )

                print(vara_result_folder / result_file.filename)
                pre, ext = os.path.splitext(vara_result_folder / result_file.filename)
                result_zip_path = Path((pre + '.zip'))
                print("------------------------------------")
                print(result_zip_path)

                #ls_cmd = ls[vara_result_folder]
                #ls_cmd()
                time_aggregate = TimeReportAggregate(result_zip_path)
                print("------------------------------------")
                print(f"Num reports {time_aggregate.reports}")
                print(f"Mean of all results {time_aggregate.mean_wall_clock_time}")

        return actions.StepResult.OK


class xzBlackboxAnalysisReport(VersionExperiment, shorthand="xzB"):

    NAME = "xzBlackboxAnalysisReport"

    REPORT_SPEC = ReportSpecification(TimeReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        #project.runtime_extension = run.RuntimeExtension(project, self) \
        #    << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))


        for x in range(2, 3):
            analysis_actions.append(
                xzBlackboxAnalysis(project, self.get_handle(), x)
            )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

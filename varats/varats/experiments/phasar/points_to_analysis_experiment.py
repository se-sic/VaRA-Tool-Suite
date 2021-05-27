"""Module for phasar points to analyses."""
import typing as tp
from os import path

import benchbuild.utils.actions as actions
from benchbuild import Project  # type: ignore
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir
from plumbum import local

from varats.report.report import FileStatusExtension as FSE
# from varats.data.reports.empty_report import EmptyReport
from varats.data.reports.points_to_analysis_perf_report import PointsToAnalysisPerfReport
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.experiment.experiment_util import (
    PEErrorHandler,
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_default_compile_error_wrapped,
    exec_func_with_pe_error_handler,
)
from varats.utils.settings import bb_cfg


class PointsToAnalysis(actions.Step):  # type: ignore
    """Analysis step to run a points to analysis on a project."""

    NAME = "PointsToAnalysis"
    DESCRIPTION = (
        "TODO: Add description"
    )
    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self,
        project: Project,
        tool
    ):
        super().__init__(obj=project, action_fn=self.analyze)
        self.tool = tool

    def analyze(self) -> actions.StepResult:
        """Run a phasar tool"""
        if not self.obj:
            return
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        varats_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", varats_result_folder)

        phasar_tool = local[self.tool]
        for binary in project.binaries:
            bc_file = get_cached_bc_file_path(project, binary)

            # Text report of analysis
            result_file = PointsToAnalysisPerfReport.get_file_name(
                project_name=str(project.name),
                binary_name=f'{self.tool}_{binary.name}',
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            # PAMM result file
            pamm_file = PointsToAnalysisPerfReport.get_supplementary_file_name(
                project_name=str(project.name),
                binary_name=f'{self.tool}_{binary.name}',
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                info_type="PAMM",
                file_ext=".json"
            )

            parameters = [bc_file, f'{varats_result_folder}/{pamm_file}']
            run_cmd = wrap_unlimit_stack_size(phasar_tool[parameters])
            run_cmd = (run_cmd > f'{varats_result_folder}/{result_file}')

            exec_func_with_pe_error_handler(
                run_cmd,
                PEErrorHandler(
                    varats_result_folder,
                    PointsToAnalysisPerfReport.get_file_name(
                        project_name=str(project.name),
                        binary_name=binary.name,
                        project_version=project.version_of_primary,
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed,
                        file_ext=".txt"
                    )
                )
            )


class PointsToAnalysisExperiment(VersionExperiment):
    """Experiment class to build and analyse a project with a custom PhASAR tool."""

    NAME = "PhasarPointsToAnalysis"

    REPORT_TYPE = PointsToAnalysisPerfReport

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            project, PointsToAnalysisPerfReport,
            PointsToAnalysis.RESULT_FOLDER_TEMPLATE
        )

        varats_result_folder = \
            f"{bb_cfg()['varats']['outfile']}/{project.name}"

        error_handler = PEErrorHandler(
            varats_result_folder,
            PointsToAnalysisPerfReport.get_file_name(
                project_name=str(project.name),
                binary_name="all",
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.CompileError,
                file_ext=".txt"
            )
        )

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project, extraction_error_handler=error_handler
        )

        analysis_actions.append(PointsToAnalysis(project, "myphasar_tool"))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""Module for custom phasar analyses."""
import typing as tp
from pathlib import Path

import benchbuild.utils.actions as actions
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir, timeout
from plumbum import local

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    wrap_unlimit_stack_size,
    get_default_compile_error_wrapped,
    exec_func_with_pe_error_handler,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification
from varats.utils.settings import bb_cfg


class Otfb(actions.Step):  # type: ignore
    """..."""

    NAME = "Otfb"
    DESCRIPTION = (
        "..."
    )

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(
        self,
        project: Project,
    ):
        super().__init__(obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """Run phasar's IDELinearConstantAnalysis analysis."""
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

        timeout_duration = '5m'

        phasar = local["evaltool"]
        for binary in project.binaries:
            bc_file = get_cached_bc_file_path(project, binary)

            result_file = EmptyReport.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            phasar_params = [bc_file]

            run_cmd = wrap_unlimit_stack_size(phasar[phasar_params])

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd] > f'{varats_result_folder}/{result_file}',
                create_default_analysis_failure_handler(
                    project, EmptyReport, 
                    Path(varats_result_folder), 
                    timeout_duration=timeout_duration
                )
            )

        return actions.StepResult.OK


class OtfbExperiment(VersionExperiment):
    """Experiment class to build and analyse a project."""

    NAME = "PhasarOtfb"

    REPORT_SPEC = ReportSpecification(EmptyReport)

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
            project, EmptyReport,
            Otfb.RESULT_FOLDER_TEMPLATE
        )

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            extraction_error_handler=create_default_compiler_error_handler(
                project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(Otfb(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

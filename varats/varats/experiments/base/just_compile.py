"""Implements an empty experiment that just compiles the project."""

import typing as tp

import benchbuild.utils.actions as actions
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.cmd import mkdir, touch

from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.empty_report import EmptyReport
from varats.experiments.wllvm import RunWLLVM
from varats.utils.experiment_util import (
    PEErrorHandler,
    VersionExperiment,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
)
from varats.utils.settings import bb_cfg


# Please take care when changing this file, see docs experiments/just_compile
class EmptyAnalysis(actions.Step):  # type: ignore
    """Empty analysis step for testing."""

    NAME = "EmptyAnslysis"
    DESCRIPTION = "Analyses nothing."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.analyze)

    def analyze(self) -> actions.StepResult:
        """Only create a report file."""
        if not self.obj:
            return
        project = self.obj

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        mkdir("-p", vara_result_folder)

        for binary in project.binaries:
            result_file = EmptyReport.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            run_cmd = touch["{res_folder}/{res_file}".format(
                res_folder=vara_result_folder, res_file=result_file
            )]

            exec_func_with_pe_error_handler(
                run_cmd,
                PEErrorHandler(
                    vara_result_folder,
                    EmptyReport.get_file_name(
                        project_name=str(project.name),
                        binary_name="all",
                        project_version=project.version_of_primary,
                        project_uuid=str(project.run_uuid),
                        extension_type=FSE.Failed
                    )
                )
            )


# Please take care when changing this file, see docs experiments/just_compile
class JustCompileReport(VersionExperiment):
    """Generates empty report file."""

    NAME = "JustCompile"

    REPORT_TYPE = EmptyReport

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            project, EmptyReport, EmptyAnalysis.RESULT_FOLDER_TEMPLATE
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(EmptyAnalysis(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

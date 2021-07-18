"""Implements an empty experiment that just compiles the project."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import mkdir, touch

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
)
from varats.experiment.wllvm import RunWLLVM
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification
from varats.utils.settings import bb_cfg


# Please take care when changing this file, see docs experiments/just_compile
class EmptyAnalysis(actions.Step):  # type: ignore
    """Empty analysis step for testing."""

    NAME = "EmptyAnslysis"
    DESCRIPTION = "Analyses nothing."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    def __init__(self, project: Project, report_spec: ReportSpecification):
        super().__init__(obj=project, action_fn=self.analyze)
        self.__report_spec = report_spec

    def analyze(self) -> actions.StepResult:
        """Only create a report file."""
        if not self.obj:
            return actions.StepResult.ERROR
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
            report_type = self.__report_spec.get_report_type("EMPTY")

            result_file = report_type.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )

            run_cmd = touch["{res_folder}/{res_file}".format(
                res_folder=vara_result_folder, res_file=result_file
            )]

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    project, report_type, Path(vara_result_folder)
                )
            )

        return actions.StepResult.OK


# Please take care when changing this file, see docs experiments/just_compile
class JustCompileReport(VersionExperiment):
    """Generates empty report file."""

    NAME = "JustCompile"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
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
            project, self.REPORT_SPEC.main_report,
            EmptyAnalysis.RESULT_FOLDER_TEMPLATE
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(EmptyAnalysis(project, self.REPORT_SPEC))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

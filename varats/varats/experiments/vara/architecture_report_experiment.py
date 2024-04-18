"""Implements an empty experiment that just compiles the project."""

import typing as tp

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import touch

from varats.data.reports.architecture_report import ArchitectureReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import RunWLLVM
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class ArchitectureAnalysis(actions.ProjectStep):  # type: ignore
    """Analyses a project's architecture with VaRA and generates a report."""

    NAME = "ArchitectureAnalysis"
    DESCRIPTION = "Analyses the bitcode with -vara-arch of VaRA."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        #

        config_id = get_current_config_id(self.project)

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, ArchitectureReport, self.project,
                binary, config_id
            )

            opt_params = [
                "-O0", "-g0", "-fvara-GB", "-S", "-fvara-arch",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary,
                    [BCFileExtensions.NO_OPT, BCFileExtensions.ARCH]
                )
            ]

            run_cmd = opt[opt_params]

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, ArchitectureReport
                )
            )

        return actions.StepResult.OK


# Please take care when changing this file, see docs experiments/just_compile
class ArchitectureReport(VersionExperiment, shorthand="ARE"):
    """Generates an Architecture report file."""

    NAME = "GenerateArchitectureReport"

    REPORT_SPEC = ReportSpecification(ArchitectureReport)

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
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(EmptyAnalysis(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

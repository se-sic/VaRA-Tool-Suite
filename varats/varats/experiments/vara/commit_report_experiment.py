"""
Implements the commit-flow report with annotating over git blame.

This class implements the commit-flow report (CFR) analysis of the variability-
aware region analyzer (VaRA). For annotation we use the git-blame data of git.
"""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.reports.commit_report import CommitReport as CR
from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    get_varats_result_folder,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    get_cached_bc_file_path,
    get_bc_cache_actions,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class CRAnalysis(actions.ProjectStep):  # type: ignore
    """Analyse a project with VaRA and generate a Commit Report."""

    NAME = "CRAnalysis"
    DESCRIPTION = "Analyses the bitcode with CR of VaRA."

    INTERACTION_FILTER_TEMPLATE = \
        "InteractionFilter-{experiment}-{project}.yaml"

    project: VProject

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        interaction_filter_experiment_name: tp.Optional[str] = None
    ):
        super().__init__(project=project)
        self.__interaction_filter_experiment_name = \
            interaction_filter_experiment_name
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct flags.
        Flags:
            -vara-CR: to run a commit flow report
            -vara-report-outfile=<path>: specify the path to store the results
        """
        if self.__interaction_filter_experiment_name is None:
            interaction_filter_file = Path(
                self.INTERACTION_FILTER_TEMPLATE.format(
                    experiment="CommitReportExperiment",
                    project=str(self.project.name)
                )
            )
        else:
            interaction_filter_file = Path(
                self.INTERACTION_FILTER_TEMPLATE.format(
                    experiment=self.__interaction_filter_experiment_name,
                    project=str(self.project.name)
                )
            )
            if not interaction_filter_file.is_file():
                raise Exception(
                    "Could not load interaction filter file \"" +
                    str(interaction_filter_file) + "\""
                )

        # Add to the user-defined path for saving the results of the
        # analysis also the name and the unique id of the project of every
        # run.
        vara_result_folder = get_varats_result_folder(self.project)

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, CR, self.project, binary
            )

            opt_params = [
                "-vara-BD", "-vara-CR", "-vara-init-commits",
                f"-vara-report-outfile={vara_result_folder}/{result_file}"
            ]

            if interaction_filter_file.is_file():
                opt_params.append(
                    f"-vara-cf-interaction-filter="
                    f"{str(interaction_filter_file)}"
                )

            opt_params.append(
                str(get_cached_bc_file_path(self.project, binary))
            )

            run_cmd = opt[opt_params]

            timeout_duration = '8h'
            from benchbuild.utils.cmd import timeout  # pylint: disable=C0415

            exec_func_with_pe_error_handler(
                timeout[timeout_duration, run_cmd],
                create_default_analysis_failure_handler(
                    self.__experiment_handle,
                    self.project,
                    CR,
                    timeout_duration=timeout_duration
                )
            )

        return actions.StepResult.OK


class CommitReportExperiment(VersionExperiment, shorthand="CRE"):
    """Generates a commit report (CR) of the project(s) specified in the
    call."""

    NAME = "GenerateCommitReport"
    REPORT_SPEC = ReportSpecification(CR)

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

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, CR
        )

        # This c-flag is provided by VaRA and it suggests to use the git-blame
        # annotation.
        project.cflags = ["-fvara-GB"]

        analysis_actions = []

        analysis_actions += get_bc_cache_actions(
            project,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(CRAnalysis(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

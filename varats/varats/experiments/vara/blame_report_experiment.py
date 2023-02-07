"""
Implements the basic blame report experiment.

The experiment analyses a project with VaRA's blame analysis and generates a
BlameReport.
"""

import typing as tp

from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmMem

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.blame_report import BlameTaintScope
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    get_varats_result_folder,
    wrap_unlimit_stack_size,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import get_cached_bc_file_path, BCFileExtensions
from varats.project.project_util import get_local_project_git_paths
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class BlameReportGeneration(actions.ProjectStep):  # type: ignore
    """Analyse a project with VaRA and generate a BlameReport."""

    NAME = "BlameReportGeneration"
    DESCRIPTION = "Analyses the bitcode with -vara-BR of VaRA."

    project: VProject

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        blame_taint_scope: BlameTaintScope
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__blame_taint_scope = blame_taint_scope

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.

        Flags used:
            * -vara-BR: to run a commit flow report
            * -yaml-report-outfile=<path>: specify the path to store the results
        """

        for binary in self.project.binaries:
            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, BR, self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-BD", "-vara-BR",
                "-vara-init-commits", "-vara-rewriteMD",
                "-vara-git-mappings=" + ",".join([
                    f'{repo}:{path}' for repo, path in
                    get_local_project_git_paths(self.project.name).items()
                ]), "-vara-use-phasar",
                f"-vara-blame-taint-scope={self.__blame_taint_scope.name}",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME
                    ]
                )
            ]

            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, BR
                )
            )

        return actions.StepResult.OK


class BlameReportExperiment(VersionExperiment, shorthand="BRE"):
    """Generates a blame report of the project(s) specified in the call."""

    NAME = "GenerateBlameReport"

    REPORT_SPEC = ReportSpecification(BR)
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]

    BLAME_TAINT_SCOPE = BlameTaintScope.COMMIT

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g0"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
        ]

        BE.setup_basic_blame_experiment(self, project, BR)

        analysis_actions = BE.generate_basic_blame_experiment_actions(
            project,
            bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )

        analysis_actions.append(
            BlameReportGeneration(
                project, self.get_handle(), self.BLAME_TAINT_SCOPE
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class BlameReportExperimentRegion(BlameReportExperiment, shorthand="BRER"):
    """Generates a blame report with region scoped taints."""

    NAME = "GenerateBlameReportRegion"
    BLAME_TAINT_SCOPE = BlameTaintScope.REGION


class BlameReportExperimentCommitInFunction(
    BlameReportExperiment, shorthand="BRECIF"
):
    """Generates a blame report with commit-in-function scoped taints."""

    NAME = "GenerateBlameReportCommitInFunction"
    BLAME_TAINT_SCOPE = BlameTaintScope.COMMIT_IN_FUNCTION

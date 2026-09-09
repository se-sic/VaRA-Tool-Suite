"""
Implements the basic blame report experiment with control-flow.

The experiment analyses a project with control and generates a
BlameReport.
"""

import typing as tp

from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmMem

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_report import BlameReport as BR, AnalysisType
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import get_cached_bc_file_path, BCFileExtensions
from varats.project.project_util import get_local_project_repos
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class CFBlameReportGeneration(actions.ProjectStep):  # type: ignore
    """Analyse a project with VaRA using control-flow and generate a BlameReport."""

    NAME = "CFBlameReportGeneration"
    DESCRIPTION = "Analyses the bitcode with control-flow of VaRA."

    project: VProject

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        analysis_type: AnalysisType
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__analysis_type = analysis_type

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
                "--passes=vara-CFG-Analyses",
                "-vara-init-commits",
                f"-vara-analysis-type={self.__analysis_type.value}",
                "-vara-git-mappings=" + ",".join([
                    f'{repo_name}:{repo.repo_path}' for repo_name, repo in
                    get_local_project_repos(self.project.name).items()
                ]),
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME
                    ]
                )
            ]

            print(f'project binaries:{self.project.binaries}: ,project_names:{self.project.name}\n')

            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, BR
                )
            )

        return actions.StepResult.OK


class CFBlameReportExperiment(VersionExperiment, shorthand="CFBR"):
    """Generates a blame report of the project(s) specified in the call with control-flow analysis."""

    NAME = "GenerateCFBlameReport"

    REPORT_SPEC = ReportSpecification(BR)
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]
    ANALYSIS_TYPE = AnalysisType.CF_DIRECT_ANALYSIS

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-passes", "-Xclang", "-disable-llvm-verifier" , "-g0"]
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
            CFBlameReportGeneration(
                project, self.get_handle(), self.ANALYSIS_TYPE
            )
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

class CFDirectReportExperiment(CFBlameReportExperiment, shorthand="CFDR"):
    """Generates a blame report with region scoped taints."""

    NAME = "GenerateBlameReportCFDirect"
    ANALYSIS_TYPE = AnalysisType.CF_DIRECT_ANALYSIS


class CFCollectiveReportExperiment(
    CFBlameReportExperiment, shorthand="CFCR"
):
    """Generates a blame report with commit-in-function scoped taints."""

    NAME = "GenerateBlameReportCFCollective"
    ANALYSIS_TYPE = AnalysisType.CF_COLLECTIVE_ANALYSIS

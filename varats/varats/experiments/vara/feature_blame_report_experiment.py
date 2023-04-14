"""
Implements the basic feature blame report experiment.
The experiment analyses a project with VaRA's blame and feature analysis and generates a
FeatureBlameReport.
"""

import typing as tp

from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmMem

import varats.experiments.vara.feature_blame_experiment as FBE
from varats.data.reports.feature_blame_report import FeatureBlameReport as FBR
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
from varats.project.project_util import get_local_project_git_paths
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class FeatureBlameReportGeneration(actions.ProjectStep):  # type: ignore
    """Analyse a project with VaRA and generate a FeatureBlameReport."""

    NAME = "FeatureBlameReportGeneration"
    DESCRIPTION = "Analyses the bitcode with -vara-FBR of VaRA."

    project: VProject

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()
    
    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.
        Flags used:
            * -vara-FBR: to run a commit feature interaction report
            * -yaml-report-outfile=<path>: specify the path to store the results
        """
        for binary in self.project.binaries:
            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, FBR, self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-PTFDD", "-vara-BD", "-vara-FBR",
                "-vara-init-commits",  "-vara-use-phasar",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME, BCFileExtensions.FEATURE
                    ]
                )
            ]
            
            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, FBR
                )
            )

            test_fbr = FBR(path=result_file.full_path())

            test_fbr.print()

        return actions.StepResult.OK
    

class FeatureBlameReportExperiment(VersionExperiment, shorthand="FBRE"):
    """Generates a feature blame report of the project(s) specified in the call."""

    NAME = "GenerateFeatureBlameReport"

    REPORT_SPEC = ReportSpecification(FBR)
    REQUIREMENTS: tp.List[Requirement] = [SlurmMem("250G")]

    def actions_for_project(
        self, project: VProject
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
            BCFileExtensions.FEATURE
        ]

        FBE.setup_basic_feature_blame_experiment(self, project, FBR)

        analysis_actions = FBE.generate_basic_feature_blame_experiment_actions(
            project,
            bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )
        analysis_actions.append(
            FeatureBlameReportGeneration(
                project, self.get_handle()
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions 
"""Implements experiments for evaluating different incremental analysis
approaches."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import mkdir, phasar_llvm_inc
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    get_varats_result_folder,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    get_default_compile_error_wrapped,
)
from varats.experiment.wllvm import (
    get_cached_bc_file_path,
    BCFileExtensions,
    get_bc_cache_actions,
    RunWLLVM,
)
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class RunAnalysisBase(actions.Step):
    """Implements the generic steps to run phasar-llvm-inc analysis comparision
    tool to compare the results of a whole-program analysis with the incremental
    one."""

    BC_FILE_EXTENSIONS = [
        BCFileExtensions.NO_OPT,
        BCFileExtensions.TBAA,
        BCFileExtensions.BLAME,
    ]

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_hash: ShortCommitHash, increment_hash: ShortCommitHash,
        analysis_flag: str
    ) -> None:
        super().__init__(obj=project, action_fn=self.run_analysis)

        self.__experiment_handle = experiment_handle
        self.__analysis_flag = analysis_flag
        self.__base_hash = base_hash
        self.__increment_hash = increment_hash

    def run_analysis(self) -> actions.StepResult:
        """Defines and runs the analysis comparision."""
        if not self.obj:
            return actions.StepResult.ERROR
        project = self.obj

        vara_result_folder = get_varats_result_folder(project)
        binary = project.binaries[0]  # we only look at one binary

        params = [
            "--module",
            get_cached_bc_file_path(
                project, binary, self.BC_FILE_EXTENSIONS, self.__base_hash
            ), "--increment",
            get_cached_bc_file_path(
                project, binary, self.BC_FILE_EXTENSIONS, self.__increment_hash
            ), "--compare-mode", self.__analysis_flag
        ]

        run_cmd = phasar_llvm_inc[params]

        run_cmd = wrap_unlimit_stack_size(run_cmd)

        exec_func_with_pe_error_handler(
            run_cmd,
            create_default_analysis_failure_handler(
                self.__experiment_handle, project, BR, Path(vara_result_folder)
            )
        )

        return actions.StepResult.OK


class RunTypeStateAnalysis(RunAnalysisBase):
    """
    Runs a type-state analysis.

    Analysis flag: --analysis typestate
    """

    NAME = "RunTypeStateAnalysis"
    DESCRIPTION = "Compare the precision of the type-state analysis."

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_hash: ShortCommitHash, increment_hash: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_hash, increment_hash,
            "--analysis typestate"
        )


class RunTaintAnalysis(RunAnalysisBase):
    """
    Runs a taint analysis.

    Analysis flag: --analysis taint
    """

    NAME = "RunTaintAnalysis"
    DESCRIPTION = "Compare the precision of the taint analysis."

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_hash: ShortCommitHash, increment_hash: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_hash, increment_hash,
            "--analysis taint"
        )


class RunLineraConstantPropagationAnalysis(RunAnalysisBase):
    """
    Runs a linear constant propagation.

    Analysis flag: --analysis lca
    """

    NAME = "RunLineraConstantPropagationAnalysis"
    DESCRIPTION = "Compare the precision of the liner constant analysis."

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_hash: ShortCommitHash, increment_hash: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_hash, increment_hash,
            "--analysis lca"
        )


class PrecisionComparisionBase(VersionExperiment, shorthand=""):

    NAME = "PrecisionComparisionBase"

    REPORT_SPEC = ReportSpecification(GlobalsReportWith, GlobalsReportWithout)

    def __init__(self, revision_step_with: int) -> None:
        self.__revision_step_with = revision_step_with

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        # Computes list of revisions that should be analyzed
        revision_list = self.compute_revisions_to_explore(project)

        analysis_actions = []

        # Generate all required bc files for analysis
        # TODO: implement loop over revisions
        analysis_actions.extend(
            get_bc_cache_actions(  # TODO: depending on the SetPRojectEnv impl,
                                   # we need to pass the revision here
                project, RunAnalysisBase.BC_FILE_EXTENSIONS,
                create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
        )

        # TODO: set commit to next state
        # analysis_actions.append(actions.SetProjectEnv(
        #                         project, get_next_commit(project.current_commit,
        #                                                  self.revision_step_with
        #                                                 )))

        analysis_actions.append(actions.Compile(project))

        current_base_hash: ShortCommitHash = revision_list[0]
        for increment_hash in revision_list[1:]:
            # Run all analysis steps
            analysis_actions.append(
                RunTypeStateAnalysis(
                    project, self.get_handle(), current_base_hash,
                    increment_hash
                )
            )
            analysis_actions.append(
                RunTaintAnalysis(
                    project, self.get_handle(), current_base_hash,
                    increment_hash
                )
            )
            analysis_actions.append(
                RunLineraConstantPropagationAnalysis(
                    project, self.get_handle(), current_base_hash,
                    increment_hash
                )
            )

            current_base_hash = increment_hash

        # Clean up the generated files afterwards
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

    def compute_revisions_to_explore(
        self, project: Project
    ) -> tp.List[ShortCommitHash]:
        """Computes the list of revisions that should be explored by this
        analysis."""
        base_hash = ShortCommitHash(project.version_of_primary)
        revisions = [base_hash]

        project.version_of_primary
        for _ in range(0, 1):
            revisions.append(
                git_get_next_rev(project, base_hash,
                                 self.__revision_step_with)  # TODO: impl
            )

        return revisions


class IncrementalAnalysisPrecisionComparisionS1(
    PrecisionComparisionBase, shorthand="IncAPCs1"
):

    def __init__(self) -> None:
        super().__init__(1)


class IncrementalAnalysisPrecisionComparisionS5(
    PrecisionComparisionBase, shorthand="IncAPCs5"
):

    def __init__(self) -> None:
        super().__init__(5)

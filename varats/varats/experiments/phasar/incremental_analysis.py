"""Implements experiments for evaluating different incremental analysis
approaches."""

import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.source.base import (
    target_prefix,
    sources_as_dict,
    Variant,
    context,
)
from benchbuild.utils import actions
from benchbuild.utils.cmd import mkdir, phasar_llvm_inc
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.blame_report import BlameReport as BR
from varats.data.reports.empty_report import EmptyReport
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
from varats.utils.git_util import (
    FullCommitHash,
    ShortCommitHash,
    get_initial_commit,
    get_all_revisions_between,
)
from varats.utils.settings import bb_cfg
from varats.utils.util import pairwise


class RunAnalysisBase(actions.Step):
    """Implements the generic steps to run phasar-llvm-inc analysis comparision
    tool to compare the results of a whole-program analysis with the incremental
    one."""

    NAME = "RunAnalysisBase"
    DESCRIPTION = "Generic comparision analysis implementation"
    BC_FILE_EXTENSIONS = [
        BCFileExtensions.NO_OPT,
        BCFileExtensions.TBAA,
        BCFileExtensions.BLAME,
    ]

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_revision: ShortCommitHash, next_revision: ShortCommitHash,
        analysis_flag: str
    ) -> None:
        super().__init__(obj=project, action_fn=self.run_analysis)

        self.__experiment_handle = experiment_handle
        self.__analysis_flag = analysis_flag
        self.__base_revision = base_revision
        self.__next_revision = next_revision

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
                project, binary, self.BC_FILE_EXTENSIONS, self.__base_revision
            ), "--increment",
            get_cached_bc_file_path(
                project, binary, self.BC_FILE_EXTENSIONS, self.__next_revision
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
        base_revision: ShortCommitHash, next_revision: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_revision, next_revision,
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
        base_revision: ShortCommitHash, next_revision: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_revision, next_revision,
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
        base_revision: ShortCommitHash, next_revision: ShortCommitHash
    ) -> None:
        super().__init__(
            project, experiment_handle, base_revision, next_revision,
            "--analysis lca"
        )


class PrecisionComparisionBase(VersionExperiment, shorthand=""):
    """Implementation base for the incremental analysis evaluation."""

    NAME = "PrecisionComparisionBase"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    MAX_REVISIONS_TO_EXPLORE = 3

    def __init__(
        self, revision_step_with: int, *args: tp.Any, **kwargs: tp.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.__revision_step_with = revision_step_with

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        # Computes list of revisions that should be analyzed
        revision_list = self.compute_revisions_to_explore(project)

        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, EmptyReport
        )

        analysis_actions = []

        analysis_actions.extend(
            get_bc_cache_actions(
                project, RunAnalysisBase.BC_FILE_EXTENSIONS,
                create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
        )

        # Generate all required bc files for analysis
        for next_revision in revision_list[1:]:
            project_variant = Variant(
                owner=sources_as_dict(*project.source)[project.primary_source],
                version=next_revision
            )
            analysis_actions.append(
                actions.SetProjectVersion(project, context(project_variant))
            )

            analysis_actions.extend(
                get_bc_cache_actions(
                    project, RunAnalysisBase.BC_FILE_EXTENSIONS,
                    create_default_compiler_error_handler(
                        self.get_handle(), project, self.REPORT_SPEC.main_report
                    )
                )
            )

        # TODO (python3.10): replace with itertools.pairwise
        for base_revision, next_revision in pairwise(reversed(revision_list)):
            print(f"Compare From: {base_revision} -> {next_revision}")
            # Run all analysis steps
            analysis_actions.append(
                RunTypeStateAnalysis(
                    project, self.get_handle(), base_revision, next_revision
                )
            )
            analysis_actions.append(
                RunTaintAnalysis(
                    project, self.get_handle(), base_revision, next_revision
                )
            )
            analysis_actions.append(
                RunLineraConstantPropagationAnalysis(
                    project, self.get_handle(), base_revision, next_revision
                )
            )

        # Clean up the generated files afterwards
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

    def compute_revisions_to_explore(
        self, project: Project
    ) -> tp.List[ShortCommitHash]:
        """Computes the list of revisions that should be explored by this
        analysis."""
        project_repo_git = Path(target_prefix()) / Path(project.primary_source)
        return get_all_revisions_between(
            get_initial_commit(project_repo_git).hash,
            project.version_of_primary, ShortCommitHash, project_repo_git
        )[::-self.__revision_step_with][:self.MAX_REVISIONS_TO_EXPLORE]


class IncrementalAnalysisPrecisionComparisionS1(
    PrecisionComparisionBase, shorthand="IncAPCs1"
):
    """Evaluation of the incremental analysis, using a 1 rev step width."""

    NAME = "IncAPCs1"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(1, *args, **kwargs)


class IncrementalAnalysisPrecisionComparisionS5(
    PrecisionComparisionBase, shorthand="IncAPCs5"
):
    """Evaluation of the incremental analysis, using a 5 rev step width."""

    NAME = "IncAPCs5"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(5, *args, **kwargs)

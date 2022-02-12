"""Implements experiments for evaluating different incremental analysis
approaches."""

import os
import shutil
import tempfile
import typing as tp
from enum import Enum
from pathlib import Path

import benchbuild as bb
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.source.base import (
    RevisionStr,
    target_prefix,
    sources_as_dict,
    Variant,
    context,
)
from benchbuild.utils import actions
from benchbuild.utils.cmd import mkdir, phasar_llvm_inc
from benchbuild.utils.requirements import Requirement, SlurmMem

from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)
from varats.data.reports.incremental_reports import (
    IncrementalReport,
    AnalysisType,
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
    get_bc_cache_actions_for_revision,
    RunWLLVM,
)
from varats.experiments.vara.blame_experiment import (
    setup_basic_blame_experiment,
    generate_basic_blame_experiment_actions,
)
from varats.project.project_util import ProjectBinaryWrapper
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


def _get_enabled_analyses() -> tp.List[AnalysisType]:
    """Allows overriding of analyses run by an experiment, this should only be
    used for testing purposes, as the experiment will not generate all the
    required results."""
    env_analysis_selection = os.getenv("PHASAR_ANALYSIS")
    if env_analysis_selection:
        return AnalysisType.convert_from(env_analysis_selection)

    return [at for at in AnalysisType]


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

    REPS = 2

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_revision: ShortCommitHash, analysis_type: AnalysisType
    ) -> None:
        super().__init__(obj=project, action_fn=self.run_analysis)

        self.__experiment_handle = experiment_handle
        self.__base_revision = base_revision
        self.__analysis_type = analysis_type

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
            )
        ]
        params += self._get_extra_parameters(project, binary)
        params += ["-D", str(self.__analysis_type)]

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            params += ["--out", Path(tmp_result_dir)]

            run_cmd = phasar_llvm_inc[params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            for _ in range(0, self.REPS):
                print(f"Running: {run_cmd}")
                exec_func_with_pe_error_handler(
                    run_cmd,
                    create_default_analysis_failure_handler(
                        self.__experiment_handle, project, IncrementalReport,
                        Path(vara_result_folder)
                    )
                )

            # Zip and persist the generated results
            result_file_name = self.__experiment_handle.get_file_name(
                IncrementalReport.shorthand(),
                project_name=str(project.name),
                binary_name=binary.name,
                project_revision=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.SUCCESS
            )
            shutil.make_archive(
                str(vara_result_folder / Path(result_file_name.filename).stem),
                "zip", Path(tmp_result_dir)
            )

        return actions.StepResult.OK

    def _get_extra_parameters(
        self, project: Project, binary: ProjectBinaryWrapper
    ) -> tp.List[str]:
        return []


class WholeProgramAnalysis(RunAnalysisBase):

    NAME = "RunWholeAnalysis"
    DESCRIPTION = "Running the configured analysis on the whole program."


class IncrementalProgramAnalysis(RunAnalysisBase):

    NAME = "RunIncrementalAnalysis"
    DESCRIPTION = "Running the configured analysis only on the increment " \
        + "between two revisison."

    def __init__(
        self, project: Project, experiment_handle: ExperimentHandle,
        base_revision: ShortCommitHash, next_revision: ShortCommitHash,
        analysis_type: AnalysisType
    ) -> None:
        super().__init__(
            project, experiment_handle, base_revision, analysis_type
        )
        self.__next_revision = next_revision

    def _get_extra_parameters(
        self, project: Project, binary: ProjectBinaryWrapper
    ) -> tp.List[str]:
        return [
            "--inc-module",
            str(
                get_cached_bc_file_path(
                    project, binary, self.BC_FILE_EXTENSIONS,
                    self.__next_revision
                )
            )
        ]


class AnalysisComparision(IncrementalProgramAnalysis):

    NAME = "RunIncWPACompAnalysis"
    DESCRIPTION = "Running the configured analysis in both, whole program and" \
        + " incremental style."

    def _get_extra_parameters(
        self, project: Project, binary: ProjectBinaryWrapper
    ) -> tp.List[str]:
        return super()._get_extra_parameters(project, binary) + [
            "--wpa-inc-in-memory-comparison"
        ]


class PrecisionComparisionBase(VersionExperiment, shorthand=""):
    """Implementation base for the incremental analysis evaluation."""

    NAME = "PrecisionComparisionBase"

    REPORT_SPEC = ReportSpecification(IncrementalReport)

    def __init__(
        self, revision_step_with: int, max_revisions_to_explore: int,
        analysis: tp.Type[IncrementalProgramAnalysis], *args: tp.Any,
        **kwargs: tp.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.__revision_step_with = revision_step_with
        self.__max_revisions_to_explore = max_revisions_to_explore
        self.__analysis = analysis

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        setup_basic_blame_experiment(
            self, project,
            self.report_spec().main_report
        )

        analysis_actions = []
        analysis_actions.extend(
            generate_basic_blame_experiment_actions(
                project, RunAnalysisBase.BC_FILE_EXTENSIONS,
                create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
        )

        # Computes list of revisions that should be analyzed
        revision_list = self.compute_revisions_to_explore(project)

        # Generate all required bc files for analysis
        for next_revision in revision_list[1:]:
            analysis_actions.append(
                actions.SetProjectVersion(
                    project, RevisionStr(next_revision.hash)
                )
            )

            analysis_actions.extend(
                get_bc_cache_actions_for_revision(
                    project, next_revision, RunAnalysisBase.BC_FILE_EXTENSIONS,
                    create_default_compiler_error_handler(
                        self.get_handle(), project, self.REPORT_SPEC.main_report
                    )
                )
            )

        # TODO (python3.10): replace with itertools.pairwise
        for base_revision, next_revision in pairwise(reversed(revision_list)):
            print(f"Compare From: {base_revision} -> {next_revision}")
            analysis_actions.append(
                actions.SetProjectVersion(
                    project, RevisionStr(next_revision.hash)
                )
            )

            for enabled_analysis_type in _get_enabled_analyses():
                # Run all analysis steps
                analysis_actions.append(
                    self.__analysis(
                        project, self.get_handle(), base_revision,
                        next_revision, enabled_analysis_type
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
        )[::-self.__revision_step_with][:self.__max_revisions_to_explore]


# Actuall, full scale experiments


class RunPhasarIncWPA(VersionExperiment, shorthand="PIWPA"):
    """Run the analyses WPA style."""

    NAME = "PIWPA"

    REPORT_SPEC = ReportSpecification(IncrementalReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:

        setup_basic_blame_experiment(
            self, project,
            self.report_spec().main_report
        )

        analysis_actions = []
        analysis_actions.extend(
            generate_basic_blame_experiment_actions(
                project, RunAnalysisBase.BC_FILE_EXTENSIONS,
                create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
        )

        for enabled_analysis_type in _get_enabled_analyses():
            analysis_actions.append(
                WholeProgramAnalysis(
                    project, self.get_handle(),
                    ShortCommitHash(project.version_of_primary),
                    enabled_analysis_type
                )
            )

        # Clean up the generated files afterwards
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunPhasarIncIncremental(PrecisionComparisionBase, shorthand="PIInc"):
    """Run the analyses incremental style."""

    NAME = "PIInc"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(1, 2, IncrementalProgramAnalysis, *args, **kwargs)


class RunPhasarIncCompare(PrecisionComparisionBase, shorthand="PIComp"):
    """Run the analyses incremental, as well as, WPA style and compare their
    results."""

    NAME = "PIComp"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(1, 2, AnalysisComparision, *args, **kwargs)


class IncrementalAnalysisPrecisionComparisionS1(
    PrecisionComparisionBase, shorthand="IncAPCs1"
):
    """Evaluation of the incremental analysis, using a 1 rev step width."""

    NAME = "IncAPCs1"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(1, 3, AnalysisComparision, *args, **kwargs)


class IncrementalAnalysisPrecisionComparisionS5(
    PrecisionComparisionBase, shorthand="IncAPCs5"
):
    """Evaluation of the incremental analysis, using a 5 rev step width."""

    NAME = "IncAPCs5"

    def __init__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        super().__init__(5, 3, AnalysisComparision, *args, **kwargs)

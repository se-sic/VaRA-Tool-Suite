"""Module for performance interaction detection experiments."""
import textwrap
import typing as tp
from itertools import pairwise
from pathlib import Path

import yaml
from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.filtertree_data import (
    InteractionFilter,
    SingleCommitFilter,
    OrOperator,
)
from varats.data.reports.performance_interaction_report import (
    PerformanceInteractionReport,
    MPRPerformanceInteractionReport,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    exec_func_with_pe_error_handler,
    create_default_analysis_failure_handler,
    ZippedExperimentSteps,
    OutputFolderStep,
)
from varats.experiment.steps.git import GitAdd, GitCommit, GitCheckout
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.experiments.base.perf_sampling import (
    PerfSampling,
    PerfSamplingSynth,
)
from varats.experiments.vara.blame_experiment import (
    setup_basic_blame_experiment,
    generate_basic_blame_experiment_actions,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.mapping.commit_map import get_commit_map
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_repos,
    ProjectBinaryWrapper,
    get_local_project_repo,
)
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider, Patch, PatchSet
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
    MPRWLFunctionOverheadReportAggregate,
)
from varats.report.report import (
    ReportSpecification,
    ReportFilename,
    BaseReport,
    ReportFilepath,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_commands import get_submodules, get_submodule_updates
from varats.utils.git_util import (
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
    get_all_revisions_between,
    get_submodule_update_commits,
)


def createCommitFilter(project: VProject) -> InteractionFilter:
    project_repo = get_local_project_repo(project.name)
    case_study = get_loaded_paper_config().get_case_studies(project.name)[0]
    commit_map = get_commit_map(project.name)
    revisions = sorted(case_study.revisions, key=commit_map.time_id)

    def rev_filter(pair: tp.Tuple[FullCommitHash, FullCommitHash]) -> bool:
        return bool(pair[1].short_hash == project.version_of_primary)

    old_rev, new_rev = list(filter(rev_filter, pairwise(revisions)))[0]

    commits = get_all_revisions_between(
        project_repo, old_rev.hash, new_rev.hash, FullCommitHash
    )[1:]

    submodules = get_submodules(project_repo)
    submodule_commits: tp.List[FullCommitHash] = []

    for submodule in submodules:
        submodule_updates = get_submodule_updates(
            project_repo,
            str(
                submodule.worktree_path.relative_to(project_repo.worktree_path)
            )
        )
        for update in submodule_updates:
            if update in commits:
                submodule_commits += get_submodule_update_commits(
                    project_repo, submodule, update
                )

    return OrOperator(
        children=[
            SingleCommitFilter(commit_hash=commit.hash) for commit in commits
        ]
    )


def get_function_overhead_report(
    report_filepath: ReportFilepath
) -> tp.Optional[WLFunctionOverheadReportAggregate]:
    return WLFunctionOverheadReportAggregate(report_filepath.full_path())


def get_old_rev(
    revisions: tp.List[FullCommitHash], project_version: ShortCommitHash
) -> ShortCommitHash:

    def rev_filter(pair: tp.Tuple[FullCommitHash, FullCommitHash]) -> bool:
        return pair[1].to_short_commit_hash() == project_version

    return list(filter(rev_filter,
                       pairwise(revisions)))[0][0].to_short_commit_hash()


def get_function_overhead_report_synth(
    report_filepath: ReportFilepath
) -> tp.Optional[WLFunctionOverheadReportAggregate]:
    return MPRWLFunctionOverheadReportAggregate(report_filepath.full_path()
                                               ).get_baseline_report()


def get_old_rev_synth(
    revisions: tp.List[FullCommitHash], project_version: ShortCommitHash
) -> ShortCommitHash:

    def rev_filter(rev: FullCommitHash) -> bool:
        return rev.to_short_commit_hash() == project_version

    return list(filter(rev_filter, revisions))[0].to_short_commit_hash()


def get_function_annotations(
    project: VProject,
    experiment_type: tp.Type[VersionExperiment],
    report_type: tp.Type[BaseReport],
    get_report: tp.Callable[[ReportFilepath],
                            tp.Optional[WLFunctionOverheadReportAggregate]],
    get_old_revision: tp.Callable[[tp.List[FullCommitHash], ShortCommitHash],
                                  ShortCommitHash],
) -> tp.List[str]:
    case_study = get_loaded_paper_config().get_case_studies(project.name)[0]
    commit_map = get_commit_map(project.name)
    revisions = sorted(case_study.revisions, key=commit_map.time_id)

    old_rev = get_old_revision(
        revisions, ShortCommitHash(project.version_of_primary)
    )

    def old_reports_filter() -> tp.Callable[[str], bool]:
        return lambda file_name: ReportFilename(
            file_name
        ).commit_hash != old_rev.to_short_commit_hash()

    report_files = get_processed_revisions_files(
        project.name,
        experiment_type,
        report_type,
        file_name_filter=old_reports_filter(),
        only_newest=False
    )

    hot_functions: tp.Set[str] = set()

    for report_filepath in report_files:
        agg_function_overhead_report = get_report(report_filepath)
        if agg_function_overhead_report is None:
            #TODO: log warning
            continue

        for _, funcs in agg_function_overhead_report.hot_functions_per_workload(
            threshold=5
        ).items():
            hot_functions.update(funcs.keys())

    print(f"Hot functions for {project.name}@{project.version_of_primary}:")
    print(hot_functions)
    return list(hot_functions)


class PerfInterReportGeneration(actions.ProjectStep):  # type: ignore
    """Step for creating a performance interaction report."""

    NAME = "PerfInterReportGeneration"
    DESCRIPTION = "Generate a performance interaction report."

    project: VProject

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        interaction_filter: InteractionFilter = SingleCommitFilter(
            commit_hash=UNCOMMITTED_COMMIT_HASH.hash
        )
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__interaction_filter = interaction_filter

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        filter_file_path = Path(
            self.project.source_of_primary
        ).parent / "interaction_filter.yaml"
        with filter_file_path.open("w") as filter_file:
            version_header = self.__interaction_filter.getVersionHeader(
            ).get_dict()
            yaml.dump_all([version_header, self.__interaction_filter],
                          filter_file)

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, PerformanceInteractionReport,
                self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-PTFDD", "-vara-FBFD", "-vara-HD",
                "-vara-BD", "-vara-PIR", "-vara-init-commits",
                "-vara-rewriteMD", "-vara-git-mappings=" + ",".join([
                    f'{repo_name}:{repo.repo_path}' for repo_name, repo in
                    get_local_project_repos(self.project.name).items()
                ]), "-vara-use-phasar",
                f"-vara-cf-interaction-filter={filter_file_path}",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME, BCFileExtensions.FEATURE,
                        BCFileExtensions.HOT_CODE
                    ]
                )
            ]

            run_cmd = wrap_unlimit_stack_size(opt[opt_params])
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project,
                    PerformanceInteractionReport
                )
            )

        return actions.StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run performance interaction analysis",
            " " * indent
        )


class PerfInterReportGenerationSynth(OutputFolderStep):
    """Step for creating a performance interaction report."""

    NAME = "PerfInterReportGenerationSynth"
    DESCRIPTION = "Generate a performance interaction report."

    project: VProject

    def __init__(
        self,
        project: Project,
        binary: ProjectBinaryWrapper,
        result_file: str,
        experiment_handle: ExperimentHandle,
        patches: tp.Optional[tp.List[Patch]] = None,
        interaction_filter: InteractionFilter = SingleCommitFilter(
            commit_hash=UNCOMMITTED_COMMIT_HASH.hash
        )
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__result_file = result_file
        self.__experiment_handle = experiment_handle
        self.__patches = patches
        self.__interaction_filter = interaction_filter

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        filter_file_path = Path(
            self.project.source_of_primary
        ).parent / "interaction_filter.yaml"
        with filter_file_path.open("w") as filter_file:
            version_header = self.__interaction_filter.getVersionHeader(
            ).get_dict()
            yaml.dump_all([version_header, self.__interaction_filter],
                          filter_file)

        opt_params = [
            "--enable-new-pm=0", "-vara-PTFDD", "-vara-FBFD", "-vara-HD",
            "-vara-BD", "-vara-PIR", "-vara-init-commits", "-vara-rewriteMD",
            "-vara-git-mappings=" + ",".join([
                f'{repo_name}:{repo.repo_path}' for repo_name, repo in
                get_local_project_repos(self.project.name).items()
            ]), "-vara-use-phasar",
            f"-vara-cf-interaction-filter={filter_file_path}",
            f"-vara-report-outfile={tmp_dir / self.__result_file}",
            get_cached_bc_file_path(
                self.project, self.__binary, [
                    BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                    BCFileExtensions.BLAME, BCFileExtensions.FEATURE,
                    BCFileExtensions.HOT_CODE
                ], self.__patches
            )
        ]

        run_cmd = wrap_unlimit_stack_size(opt[opt_params])
        exec_func_with_pe_error_handler(
            run_cmd,
            create_default_analysis_failure_handler(
                self.__experiment_handle, self.project,
                self.__experiment_handle.report_spec().main_report
            )
        )

        return actions.StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run performance interaction analysis",
            " " * indent
        )


class PerformanceInteractionExperiment(VersionExperiment, shorthand="PIE"):
    """Performance interaction analysis for real-world projects."""

    NAME = "PerfInteractions"

    REPORT_SPEC = ReportSpecification(PerformanceInteractionReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        case_study = get_loaded_paper_config().get_case_studies(project.name)[0]
        commit_map = get_commit_map(project.name)
        revisions = sorted(case_study.revisions, key=commit_map.time_id)
        if project.version_of_primary == revisions[0].short_hash:
            return []

        setup_basic_blame_experiment(
            self, project, PerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        hot_funcs = get_function_annotations(
            project, PerfSampling, WLFunctionOverheadReportAggregate,
            get_function_overhead_report, get_old_rev
        )
        project.cflags.extend([
            "-fvara-handleRM=High",
            f"-fvara-highlight-function={','.join(hot_funcs)}"
        ])
        project.cflags += [
            "-O1", "-Xclang", "-disable-llvm-optzns", "-g0", "-fuse-ld=lld"
        ]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
            BCFileExtensions.FEATURE,
            BCFileExtensions.HOT_CODE,
        ]

        analysis_actions = []

        analysis_actions += generate_basic_blame_experiment_actions(
            project,
            bc_file_extensions,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )
        analysis_actions.append(
            PerfInterReportGeneration(
                project, self.get_handle(), createCommitFilter(project)
            )
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class PerformanceInteractionExperimentSynthetic(
    VersionExperiment, shorthand="PIES"
):
    """Performance-interaction analysis for synthetic case studies."""

    NAME = "PerfInteractionsSynth"

    REPORT_SPEC = ReportSpecification(MPRPerformanceInteractionReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        setup_basic_blame_experiment(
            self, project, MPRPerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        hot_funcs = get_function_annotations(
            project, PerfSamplingSynth, MPRWLFunctionOverheadReportAggregate,
            get_function_overhead_report_synth, get_old_rev_synth
        )
        project.cflags.extend([
            "-fvara-handleRM=High",
            f"-fvara-highlight-function={','.join(hot_funcs)}"
        ])
        project.cflags += [
            "-O1", "-Xclang", "-disable-llvm-optzns", "-g0", "-fuse-ld=lld"
        ]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
            BCFileExtensions.FEATURE,
            BCFileExtensions.HOT_CODE,
        ]

        patch_provider = PatchProvider.get_provider_for_project(project)
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )
        perf_region_patches = patches["perf_region"]
        regression_patches = patches.all_of("perf_inter", "regression")
        change_patches = patches.all_of("perf_inter", "change")

        analysis_actions = []

        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report, project, binary
            )

            # simulate regressions via patches
            patch_steps = []
            for change_patch in change_patches:
                # apply performance region patches
                applied_patches = list(perf_region_patches)
                for perf_region_patch in perf_region_patches:
                    patch_steps.append(ApplyPatch(project, perf_region_patch))

                # apply separate regression simulating patch if available
                #TODO: use tags to match patches
                patch_id = change_patch.shortname[-1]
                filtered_regression_patches = list(
                    filter(
                        lambda patch: patch.shortname[-1] == patch_id,
                        regression_patches
                    )
                )
                if filtered_regression_patches:
                    assert len(filtered_regression_patches) == 1
                    regression_patch = filtered_regression_patches[0]
                    applied_patches.append(regression_patch)
                    patch_steps.append(ApplyPatch(project, regression_patch))

                # commit patches to not interfere with the change patch
                patch_steps.append(GitAdd(project, "-u"))
                patch_steps.append(
                    GitCommit(
                        project, message="Hot code and regression patches"
                    )
                )

                # apply change patch
                patch_steps.append(ApplyPatch(project, change_patch))
                applied_patches.append(change_patch)

                # experiment steps
                patch_steps += generate_basic_blame_experiment_actions(
                    project,
                    bc_file_extensions,
                    applied_patches,
                    extraction_error_handler=
                    create_default_compiler_error_handler(
                        self.get_handle(), project, self.REPORT_SPEC.main_report
                    )
                )
                patch_steps.append(
                    PerfInterReportGenerationSynth(
                        project, binary,
                        MPRPerformanceInteractionReport.
                        create_patched_report_name(
                            change_patch, "performance_interactions"
                        ), self.get_handle(), applied_patches
                    )
                )
                patch_steps.append(RevertPatch(project, change_patch))

                # checkout original project revision
                patch_steps.append(
                    GitCheckout(
                        project, ShortCommitHash(project.version_of_primary)
                    )
                )

            analysis_actions.append(
                ZippedExperimentSteps(result_filepath, patch_steps)
            )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""Module for performance interaction detection experiments."""

import sys
import textwrap
import typing as tp
from pathlib import Path

import yaml
from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.filtertree_data import (
    SingleCommitFilter,
)
from varats.data.reports.performance_interaction_report import (
    MPRPerformanceInteractionReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    OutputFolderStep,
    VersionExperiment,
    ZippedExperimentSteps,
    create_default_analysis_failure_handler,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    exec_func_with_pe_error_handler,
    wrap_unlimit_stack_size,
)
from varats.experiment.steps.git import GitAdd, GitCheckout, GitCommit
from varats.experiment.steps.patch import ApplyPatch
from varats.experiment.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.experiments.base.perf_sampling import (
    PerfSamplingSynth,
)
from varats.experiments.vara.blame_experiment import (
    generate_basic_blame_experiment_actions,
    setup_basic_blame_experiment,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.experiments.vara.performance_interaction import (
    get_function_annotations,
)
from varats.jupyterhelper.file import load_mpr_performance_interaction_report
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_repos,
)
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import Patch, PatchProvider
from varats.report.function_overhead_report import (
    MPRWLFunctionOverheadReportAggregate,
    WLFunctionOverheadReportAggregate,
)
from varats.report.report import (
    ReportFilename,
    ReportFilepath,
    ReportSpecification,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import (
    FullCommitHash,
    RepositoryHandle,
    ShortCommitHash,
    get_head_commit,
)

if sys.version_info.minor < 12:
    from typing_extensions import override
else:
    from typing import override


def get_function_overhead_report_synth(
    report_filepath: ReportFilepath,
) -> WLFunctionOverheadReportAggregate | None:
    """Loads the specified report if available."""
    return MPRWLFunctionOverheadReportAggregate(
        report_filepath.full_path()
    ).get_baseline_report()


def get_old_rev_synth(
    _: list[FullCommitHash], project_revision: ShortCommitHash
) -> ShortCommitHash:
    """
    Finds the old revision for the given project revision.

    For experiments with synthetic regressions, this is simply the project
    revision.

    Args:
        _: list of available revisions sorted from old to new
        project_revision: current project revision

    Returns:
        The old revision.
    """
    return project_revision


def get_patch_filter(project: Project) -> tp.Callable[[Patch], bool]:
    """
    Creates a filter for selecting patches to be used in this experiment.

    This skips patches for which a successful report already exists.
    """
    def file_name_filter(file_name: str) -> bool:
        rfn = ReportFilename(file_name)
        return rfn.commit_hash.hash != project.version_of_primary

    report_files = get_processed_revisions_files(
        project.name,
        PerformanceInteractionExperimentSynthetic,
        file_name_filter=file_name_filter,
    )

    if not report_files:
        return lambda _: True

    patches: list[str] = []

    for report_file in report_files:
        report = load_mpr_performance_interaction_report(report_file)
        patches += report.get_patch_names()

    def patch_filter(patch: Patch) -> bool:
        return patch.shortname not in patches

    return patch_filter


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
        patches: list[Patch] | None = None,
    ) -> None:
        """Creates a step for creating a performance interaction report."""
        super().__init__(project=project)
        self.__binary = binary
        self.__result_file = result_file
        self.__experiment_handle = experiment_handle
        self.__patches = patches

    def call_with_output_folder(self, tmp_dir: Path) -> actions.StepResult:
        """
        Runs performance interaction analysis.

        This step generates a performance interaction report for the given
        project using VaRA's performance interaction creator pass. It stores the
        report in the provided temporary folder.

        Returns:
            OK if the analysis was successful, ERROR otherwise.
        """
        repo = RepositoryHandle(Path(self.project.source_of_primary))
        head = get_head_commit(repo)
        interaction_filter = SingleCommitFilter(commit_hash=head.hash)

        filter_file_path = repo.worktree_path.parent / "interaction_filter.yaml"
        with filter_file_path.open("w") as filter_file:
            version_header = interaction_filter.getVersionHeader().get_dict()
            yaml.dump_all([version_header, interaction_filter], filter_file)

        opt_params = [
            "-passes=vara-rewriteMD,vara-PIR",
            "-vara-feature-detection=PTFDD,FBFD",
            "-vara-init-commits",
            "-vara-use-phasar",
            "-vara-git-mappings="
            + ",".join(
                [
                    f'{repo_name}:{repo.repo_path}'
                    for repo_name, repo in get_local_project_repos(
                        self.project.name
                    ).items()
                ]
            ),
            f"-vara-cf-interaction-filter={filter_file_path}",
            f"-vara-report-outfile={tmp_dir / self.__result_file}",
            # TODO: cached bc files from previous runs won't work
            #       because commit hashes from patches are not stable.
            get_cached_bc_file_path(
                self.project,
                self.__binary,
                [
                    BCFileExtensions.NO_OPT,
                    BCFileExtensions.TBAA,
                    BCFileExtensions.BLAME,
                    BCFileExtensions.FEATURE,
                    BCFileExtensions.HOT_CODE,
                ],
                self.__patches,
            ),
        ]

        run_cmd = wrap_unlimit_stack_size(opt[opt_params])
        exec_func_with_pe_error_handler(
            run_cmd,
            create_default_analysis_failure_handler(
                self.__experiment_handle,
                self.project,
                self.__experiment_handle.report_spec().main_report,
            ),
        )

        return actions.StepResult.OK

    @override
    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run performance interaction analysis",
            " " * indent,
        )


class PerformanceInteractionExperimentSynthetic(
    VersionExperiment, shorthand="PIES"
):
    """Performance-interaction analysis for synthetic regression scenarios."""

    NAME = "PerfInteractionsSynth"

    REPORT_SPEC = ReportSpecification(MPRPerformanceInteractionReport)

    @override
    def actions_for_vproject(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        case_study = next(
            iter(get_loaded_paper_config().get_case_studies(project.name))
        )

        setup_basic_blame_experiment(
            self, project, MPRPerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        hot_funcs = get_function_annotations(
            project.name,
            ShortCommitHash(project.version_of_primary),
            case_study,
            PerfSamplingSynth,
            MPRWLFunctionOverheadReportAggregate,
            get_function_overhead_report_synth,
            get_old_rev_synth,
        )
        project.cflags.extend(
            [
                "-fvara-handleRM=High",
                f"-fvara-highlight-function={','.join(hot_funcs)}",
            ]
        )
        project.cflags += [
            "-O1",
            "-Xclang",
            "-disable-llvm-passes",
            "-Xclang",
            "-disable-llvm-verifier",
            "-g0",
            "-fuse-ld=lld",
        ]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
            BCFileExtensions.FEATURE,
            BCFileExtensions.HOT_CODE,
        ]

        patch_provider = PatchProvider.get_provider_for_project(type(project))
        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )
        change_patches = patches.all_of("perf_inter", "change")

        analysis_actions: tp.MutableSequence[actions.Step] = []

        for binary in project.binaries:
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report,
                project,
                binary,
            )

            # simulate regressions via patches
            patch_steps = []
            for change_patch in filter(
                get_patch_filter(project), change_patches
            ):
                applied_patches = [change_patch]
                patch_steps.extend(
                    (
                        ApplyPatch(project, change_patch),
                        GitAdd(project, "-u"),
                        GitCommit(
                            project, message="Change patch", no_verify=True
                        ),
                    )
                )

                # experiment steps
                patch_steps += generate_basic_blame_experiment_actions(
                    project,
                    bc_file_extensions,
                    applied_patches,
                    use_blame_server=False,
                    extraction_error_handler=create_default_compiler_error_handler(
                        self.get_handle(), project, self.REPORT_SPEC.main_report
                    ),
                )
                patch_steps.append(
                    PerfInterReportGenerationSynth(
                        project,
                        binary,
                        MPRPerformanceInteractionReport.create_patched_report_name(
                            change_patch, "performance_interactions"
                        ),
                        self.get_handle(),
                        applied_patches,
                    )
                )

                # check out original project revision
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

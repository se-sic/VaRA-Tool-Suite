"""Module for performance interaction detection experiments."""
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
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    exec_func_with_pe_error_handler,
    create_default_analysis_failure_handler,
)
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.experiments.vara.blame_experiment import (
    setup_basic_blame_experiment,
    generate_basic_blame_experiment_actions,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.mapping.commit_map import get_commit_map
from varats.paper.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git_paths,
    get_local_project_git_path,
)
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.report import ReportSpecification
from varats.utils.git_util import (
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
    get_all_revisions_between,
)


def createCommitFilter(project: VProject) -> InteractionFilter:
    project_git_path = get_local_project_git_path(project.name)
    case_study = get_loaded_paper_config().get_case_studies(project.name)[0]
    commit_map = get_commit_map(project.name)
    revisions = sorted(case_study.revisions, key=commit_map.time_id)

    def rev_filter(pair: tp.Tuple[FullCommitHash, FullCommitHash]) -> bool:
        return pair[1].short_hash == project.version_of_primary

    old_rev, new_rev = list(filter(rev_filter, pairwise(revisions)))[0]

    commits = get_all_revisions_between(
        old_rev.hash, new_rev.hash, FullCommitHash, project_git_path
    )[1:]

    return OrOperator(
        children=[
            SingleCommitFilter(commit_hash=commit.hash) for commit in commits
        ]
    )


def get_function_annotations(project_name: str) -> tp.List[str]:
    return {
        "bzip2": [
            "BZ2_decompress", "BZ2_bzDecompress", "BZ2_compressBlock",
            "BZ2_blockSort", "mainGtU", "sendMTFValues", "handle_compress"
        ],
        "picosat": [
            "propl", "prop2", "unassign", "analyze",
            "should_disconnect_head_tail", "assign_phase", "collect_clauses"
        ]
    }[project_name]


class PerfInterReportGeneration(actions.ProjectStep):
    """Step for creating a performance interaction report."""

    NAME = "PerfInterReportGeneration"
    DESCRIPTION = "Generate a performance interaction report."

    project: VProject

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
        interactionFilter: InteractionFilter = SingleCommitFilter(
            commit_hash=UNCOMMITTED_COMMIT_HASH.hash
        )
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__interaction_filter = interactionFilter

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
                    f'{repo}:{path}' for repo, path in
                    get_local_project_git_paths(self.project.name).items()
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


class PerformanceInteractionExperiment(VersionExperiment, shorthand="PIE"):
    """"""

    NAME = "PerfInteractions"

    REPORT_SPEC = ReportSpecification(PerformanceInteractionReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        setup_basic_blame_experiment(
            self, project, PerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        project.cflags.extend([
            "-fvara-handleRM=High",
            f"-fvara-highlight-function={','.join(get_function_annotations(project.name))}"
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
    """"""

    NAME = "PerfInteractionsSynth"

    REPORT_SPEC = ReportSpecification(PerformanceInteractionReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        setup_basic_blame_experiment(
            self, project, PerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        project.cflags.extend(["-fvara-handleRM=High"])
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
        regression_patches = patches["regression"]
        print(f"{regression_patches=}")

        analysis_actions = []
        # highlight performance regions via patch
        for patch in perf_region_patches:
            analysis_actions.append(ApplyPatch(project, patch))

        # apply regressions via patch
        for patch in regression_patches:
            analysis_actions.append(ApplyPatch(project, patch))
            analysis_actions += generate_basic_blame_experiment_actions(
                project,
                bc_file_extensions,
                extraction_error_handler=create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
            analysis_actions.append(
                PerfInterReportGeneration(project, self.get_handle())
            )
            analysis_actions.append(RevertPatch(project, patch))

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

"""Module for performance interaction detection experiments."""
import typing as tp
from pathlib import Path

import yaml
from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

from varats.data.filtertree_data import InteractionFilter, SingleCommitFilter
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
from varats.project.project_util import get_local_project_git_paths
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider
from varats.report.report import ReportSpecification
from varats.utils.git_util import ShortCommitHash, UNCOMMITTED_COMMIT_HASH


def createCommitFilter() -> InteractionFilter:
    return SingleCommitFilter(commit_hash=UNCOMMITTED_COMMIT_HASH.hash)


class PerfInterReportGeneration(actions.ProjectStep):
    """Step for creating a performance interaction report."""

    NAME = "PerfInterReportGeneration"
    DESCRIPTION = "Generate a performance interaction report."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

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

        interaction_filter = createCommitFilter()
        filter_file_path = Path(
            self.project.source_of_primary
        ).parent / "interaction_filter.yaml"
        with filter_file_path.open("w") as filter_file:
            version_header = interaction_filter.getVersionHeader().get_dict()
            yaml.dump_all([version_header, interaction_filter], filter_file)

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, PerformanceInteractionReport,
                self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-PTFDD", "-vara-HD", "-vara-BD",
                "-vara-PIR", "-vara-init-commits", "-vara-rewriteMD",
                "-vara-git-mappings=" + ",".join([
                    f'{repo}:{path}' for repo, path in
                    get_local_project_git_paths(self.project.name).items()
                ]), "-vara-use-phasar",
                f"-vara-cf-interaction-filter={filter_file_path}",
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME, BCFileExtensions.FEATURE
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
        project.cflags.append("-fvara-handleRM=High")
        # project.cflags += ["-O1", "-g0"]
        project.cflags += [
            "-O1", "-Xclang", "-disable-llvm-optzns", "-g0", "-fuse-ld=lld"
        ]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
            BCFileExtensions.FEATURE,
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

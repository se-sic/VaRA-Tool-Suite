"""Module for performance interaction detection experiments."""

import logging
import sys
import textwrap
import typing as tp
from itertools import pairwise
from pathlib import Path

import yaml
from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt
from benchbuild.utils.requirements import Requirement, SlurmExclusive, SlurmMem

from varats.data.filtertree_data import (
    InteractionFilter,
    OrOperator,
    SingleCommitFilter,
)
from varats.data.reports.performance_interaction_report import (
    PerformanceInteractionReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    create_default_analysis_failure_handler,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    exec_func_with_pe_error_handler,
    wrap_unlimit_stack_size,
)
from varats.experiment.wllvm import BCFileExtensions, get_cached_bc_file_path
from varats.experiments.base.perf_sampling import (
    PerfSampling,
)
from varats.experiments.vara.blame_experiment import (
    generate_basic_blame_experiment_actions,
    setup_basic_blame_experiment,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.mapping.commit_map import get_commit_map
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import CaseStudy
from varats.project.project_util import (
    get_local_project_repo,
    get_local_project_repos,
)
from varats.project.varats_project import VProject
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
)
from varats.report.report import (
    BaseReport,
    ReportFilename,
    ReportFilepath,
    ReportSpecification,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import (
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
    ShortCommitHash,
    get_all_revisions_between,
)

if sys.version_info.minor < 12:
    from typing_extensions import override
else:
    from typing import override


if tp.TYPE_CHECKING:
    from varats.paper.case_study import CSStage

LOG = logging.getLogger(__name__)


def create_commit_filter(
    project: VProject, case_study: CaseStudy
) -> InteractionFilter | None:
    """
    Creates a commit filter for the given project instance.

    The commit filter accepts all commits between the currently analyzed commit
    (inclusive) and the next older commit in the same paper config stage
    (exclusive).

    Args:
        project: project for which to create the commit filter
        case_study: case study used to find previous revision

    Returns:
        The created commit filter.
    """
    project_repo = get_local_project_repo(project.name)
    case_study = get_loaded_paper_config().get_case_studies(project.name)[0]
    commit_map = get_commit_map(project.name)
    stage: CSStage | None = None

    for s in case_study.stages:
        if s.has_revision(ShortCommitHash(project.version_of_primary)):
            stage = s
            break

    if stage is None:
        return None

    revisions = sorted(stage.revisions, key=commit_map.time_id)

    def rev_filter(pair: tuple[FullCommitHash, FullCommitHash]) -> bool:
        return bool(pair[1].short_hash == project.version_of_primary)

    filtered_revs = list(filter(rev_filter, pairwise(revisions)))
    if len(filtered_revs) < 0:
        return None

    old_rev, new_rev = filtered_revs[0]
    commits = get_all_revisions_between(
        project_repo, old_rev.hash, new_rev.hash, FullCommitHash
    )[1:]

    return OrOperator(
        children=[
            SingleCommitFilter(commit_hash=commit.hash) for commit in commits
        ]
    )


def get_function_overhead_report(
    report_filepath: ReportFilepath,
) -> WLFunctionOverheadReportAggregate | None:
    """Loads the specified report if available."""
    return WLFunctionOverheadReportAggregate(report_filepath.full_path())


def get_old_rev(
    revisions: list[FullCommitHash], project_revision: ShortCommitHash
) -> ShortCommitHash:
    """
    Finds the old revision for the given project revision.

    The old revision is the newest revision in `revisions` that is older than
    `project_revision`.

    Args:
        revisions: list of available revisions sorted from old to new
        project_revision: current project revision

    Returns:
        The old revision.
    """

    def rev_filter(pair: tuple[FullCommitHash, FullCommitHash]) -> bool:
        return pair[1].to_short_commit_hash() == project_revision

    return next(filter(rev_filter, pairwise(revisions)))[
        0
    ].to_short_commit_hash()


def get_function_annotations(
    project_name: str,
    project_version: ShortCommitHash,
    case_study: CaseStudy,
    experiment_type: type[VersionExperiment],
    report_type: type[BaseReport],
    get_report: tp.Callable[
        [ReportFilepath], WLFunctionOverheadReportAggregate | None
    ],
    get_old_revision: tp.Callable[
        [list[FullCommitHash], ShortCommitHash], ShortCommitHash
    ],
) -> list[str]:
    """
    Determines which functions to mark as hot code for the experiment.

    To determine what is hot code, we look at a performance profile created on
    an old revision of the project, that is, the latest version before the
    current one in the case study.

    Args:
        project_name: name of the project under investigation
        project_version: version of the project under investigation
        case_study: case study used in the experiment
        experiment_type: the experiment used to create the reports with hot
                         code information.
        report_type: the report type containing hot code information
        get_report: function used for loading the report
        get_old_revision: function used for finding the old revision used in the
                          experiment

    Returns:
        A list of function names considered hot code.
    """
    commit_map = get_commit_map(project_name)
    revisions = sorted(case_study.revisions, key=commit_map.time_id)
    old_rev = get_old_revision(revisions, project_version)

    def old_reports_filter() -> tp.Callable[[str], bool]:
        return lambda file_name: (
            ReportFilename(file_name).commit_hash
            != old_rev.to_short_commit_hash()
        )

    report_files = get_processed_revisions_files(
        project_name,
        experiment_type,
        report_type,
        file_name_filter=old_reports_filter(),
        only_newest=False,
    )

    hot_functions: set[str] = set()

    for report_filepath in report_files:
        agg_function_overhead_report = get_report(report_filepath)
        if agg_function_overhead_report is None:
            LOG.warning(
                f"{project_name}@{project_version}: "
                "No function overhead data found!"
            )
            continue

        for _, funcs in agg_function_overhead_report.hot_functions_per_workload(
            threshold=5
        ).items():
            hot_functions.update(funcs.keys())

    LOG.info(
        f"Hot functions for {project_name}@{project_version}: {hot_functions}"
    )
    return list(hot_functions)


class PerfInterReportGeneration(actions.ProjectStep):
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
        ),
    ) -> None:
        """Creates a step for creating a performance interaction report."""
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__interaction_filter = interaction_filter

    def __call__(self) -> actions.StepResult:
        """Calls this step's `analyze()` function."""
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """
        Runs performance interaction analysis.

        This step generates a performance interaction report for the given
        project using VaRA's performance interaction creator pass.

        Returns:
            OK if the analysis was successful, ERROR otherwise.
        """
        filter_file_path = (
            Path(self.project.source_of_primary).parent
            / "interaction_filter.yaml"
        )
        with filter_file_path.open("w") as filter_file:
            version_header = (
                self.__interaction_filter.getVersionHeader().get_dict()
            )
            yaml.dump_all(
                [version_header, self.__interaction_filter], filter_file
            )

        for binary in self.project.binaries:
            result_file = create_new_success_result_filepath(
                self.__experiment_handle,
                PerformanceInteractionReport,
                self.project,
                binary,
            )

            opt_params = [
                "-passes=vara-rewriteMD,vara-PIR",
                "-vara-feature-detection=FBFD,PTFDD",
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
                f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project,
                    binary,
                    [
                        BCFileExtensions.NO_OPT,
                        BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME,
                        BCFileExtensions.FEATURE,
                        BCFileExtensions.HOT_CODE,
                    ],
                ),
            ]

            run_cmd = wrap_unlimit_stack_size(opt[opt_params])
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle,
                    self.project,
                    PerformanceInteractionReport,
                ),
            )

        return actions.StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        """Prints a short description of this step."""
        return textwrap.indent(
            f"* {self.project.name}: Run performance interaction analysis",
            " " * indent,
        )


class PerformanceInteractionExperiment(VersionExperiment, shorthand="PIE"):
    """Performance interaction analysis for real-world regression scenarios."""

    NAME = "PerfInteractions"

    REPORT_SPEC = ReportSpecification(PerformanceInteractionReport)
    REQUIREMENTS: list[Requirement] = [  # ruff: ignore[mutable-class-default]
        SlurmMem("250G"),
        SlurmExclusive(),
    ]

    @override
    def actions_for_vproject(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        case_study = next(
            iter(get_loaded_paper_config().get_case_studies(project.name))
        )
        commit_filter = create_commit_filter(project, case_study)

        if commit_filter is None:
            # No "old" project version exists -> skip analysis
            return []

        setup_basic_blame_experiment(
            self, project, PerformanceInteractionReport
        )
        project.cflags += FeatureExperiment.get_vara_feature_cflags(project)
        hot_funcs = get_function_annotations(
            project.name,
            ShortCommitHash(project.version_of_primary),
            case_study,
            PerfSampling,
            WLFunctionOverheadReportAggregate,
            get_function_overhead_report,
            get_old_rev,
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

        analysis_actions = generate_basic_blame_experiment_actions(
            project,
            bc_file_extensions,
            use_blame_server=False,
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            ),
        )
        analysis_actions.append(
            PerfInterReportGeneration(project, self.get_handle(), commit_filter)
        )

        analysis_actions.append(actions.Clean(project))

        return analysis_actions

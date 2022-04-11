"""A case study is used to pin down the exact set of revisions that should be
analysed for a project."""
import logging
import random
import typing as tp
from collections import defaultdict
from datetime import datetime
from enum import Enum
from itertools import groupby
from pathlib import Path

import pygit2
from benchbuild import Project

from varats.base.sampling_method import NormalSamplingMethod
from varats.data.reports.szz_report import (
    SZZReport,
    SZZUnleashedReport,
    PyDrillerSZZReport,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_tagged_experiment_specific_revisions,
)
from varats.jupyterhelper.file import (
    load_szzunleashed_report,
    load_pydriller_szz_report,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.project.project_util import (
    get_project_cls_by_name,
    get_local_project_git_path,
)
from varats.provider.bug.bug import RawBug
from varats.provider.bug.bug_provider import BugProvider
from varats.provider.release.release_provider import (
    ReleaseProvider,
    ReleaseType,
)
from varats.report.report import FileStatusExtension, BaseReport, ReportFilename
from varats.revision.revisions import (
    get_failed_revisions,
    get_processed_revisions,
    get_tagged_revision,
    get_tagged_revisions,
    filter_blocked_revisions,
    is_revision_blocked,
    get_processed_revisions_files,
)
from varats.utils.git_util import (
    ShortCommitHash,
    FullCommitHash,
    contains_source_code,
    ChurnConfig,
)

LOG = logging.Logger(__name__)


class ExtenderStrategy(Enum):
    """Enum for all currently supported extender strategies."""
    value: int  # pylint: disable=invalid-name

    MIXED = -1
    SIMPLE_ADD = 1
    DISTRIB_ADD = 2
    SMOOTH_PLOT = 3
    PER_YEAR_ADD = 4
    RELEASE_ADD = 5
    ADD_BUGS = 6


def newest_processed_revision_for_case_study(
    case_study: CaseStudy, result_file_type: tp.Type[BaseReport]
) -> tp.Optional[FullCommitHash]:
    """
    Computes the newest revision of this case study that has been processed.

    Args:
        case_study: to work on
        result_file_type: report type of the result files

    Returns:
        the newest processed revision if available
    """
    processed_revisions = processed_revisions_for_case_study(
        case_study, result_file_type
    )
    if not processed_revisions:
        return None

    commit_map = get_commit_map(case_study.project_name)
    processed_revisions.sort(key=commit_map.time_id, reverse=True)
    return processed_revisions[0]


def processed_revisions_for_case_study(
    case_study: CaseStudy, result_file_type: tp.Type[BaseReport]
) -> tp.List[FullCommitHash]:
    """
    Computes all revisions of this case study that have been processed.

    Args:
        case_study: to work on
        result_file_type: report type of the result files

    Returns:
        a list of processed revisions
    """
    total_processed_revisions = get_processed_revisions(
        case_study.project_name, result_file_type
    )

    return [
        rev for rev in case_study.revisions
        if rev.to_short_commit_hash() in total_processed_revisions
    ]


def failed_revisions_for_case_study(
    case_study: CaseStudy, result_file_type: tp.Type[BaseReport]
) -> tp.List[FullCommitHash]:
    """
    Computes all revisions of this case study that have failed.

    Args:
        case_study: to work on
        result_file_type: report type of the result files

    Returns:
        a list of failed revisions
    """
    total_failed_revisions = get_failed_revisions(
        case_study.project_name, result_file_type
    )

    return [
        rev for rev in case_study.revisions
        if rev.to_short_commit_hash() in total_failed_revisions
    ]


def get_revisions_status_for_case_study(
    case_study: CaseStudy,
    result_file_type: tp.Type[BaseReport],
    stage_num: int = -1,
    tag_blocked: bool = True,
    experiment_type: tp.Optional[tp.Type[VersionExperiment]] = None
) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
    """
    Computes the file status for all revisions in this case study.

    Args:
        case_study: to work on
        result_file_type: report type of the result files
        stage_num: only consider a specific stage of the case study
        tag_blocked: if true, also blocked commits are tagged

    Returns:
        a list of (revision, status) tuples
    """
    try:
        project_cls = get_project_cls_by_name(case_study.project_name)
    except LookupError:
        # Return an empty list should a project name not exist.
        return []

    if experiment_type:
        tagged_revisions = get_tagged_experiment_specific_revisions(
            project_cls, result_file_type, tag_blocked, experiment_type
        )
    else:
        tagged_revisions = get_tagged_revisions(
            project_cls, result_file_type, tag_blocked
        )

    def filtered_tagged_revs(
        rev_provider: tp.Iterable[FullCommitHash]
    ) -> tp.List[tp.Tuple[ShortCommitHash, FileStatusExtension]]:
        filtered_revisions = []
        for rev in rev_provider:
            short_rev = rev.to_short_commit_hash()
            found = False
            for tagged_rev in tagged_revisions:
                if short_rev == tagged_rev[0]:
                    filtered_revisions.append(tagged_rev)
                    found = True
                    break
            if not found:
                if tag_blocked and is_revision_blocked(short_rev, project_cls):
                    filtered_revisions.append(
                        (short_rev, FileStatusExtension.BLOCKED)
                    )
                else:
                    filtered_revisions.append(
                        (short_rev, FileStatusExtension.MISSING)
                    )
        return filtered_revisions

    if stage_num == -1:
        return filtered_tagged_revs(case_study.revisions)

    if stage_num < case_study.num_stages:
        stage = case_study.stages[stage_num]
        return filtered_tagged_revs(stage.revisions)

    return []


def get_revision_status_for_case_study(
    case_study: CaseStudy,
    revision: ShortCommitHash,
    result_file_type: tp.Type[BaseReport],
) -> FileStatusExtension:
    """
    Computes the file status for the given revision in this case study.

    Args:
        case_study: to work on
        revision: to compute status for
        result_file_type: report type of the result files

    Returns:
        a list of (revision, status) tuples
    """
    if not case_study.has_revision(revision):
        raise ValueError(f"Case study has no revision {revision}")

    return get_tagged_revision(
        revision, case_study.project_name, result_file_type
    )


def get_newest_result_files_for_case_study(
    case_study: CaseStudy, result_dir: Path, report_type: tp.Type[BaseReport]
) -> tp.List[Path]:
    """
    Return all result files of a specific type that belong to a given case
    study. For revision with multiple files, the newest file will be selected.

    Args:
        case_study: to load
        result_dir: to load the results from
        report_type: type of report that should be loaded

    Returns:
        list of result file paths
    """
    files_to_store: tp.Dict[ShortCommitHash, Path] = {}

    result_dir /= case_study.project_name
    if not result_dir.exists():
        return []

    for opt_res_file in result_dir.iterdir():
        report_file = ReportFilename(opt_res_file.name)
        if report_type.is_correct_report_type(report_file.filename):
            commit_hash = report_file.commit_hash
            if case_study.has_revision(commit_hash):
                current_file = files_to_store.get(commit_hash, None)
                if current_file is None:
                    files_to_store[commit_hash] = opt_res_file
                else:
                    if (
                        current_file.stat().st_mtime <
                        opt_res_file.stat().st_mtime
                    ):
                        files_to_store[commit_hash] = opt_res_file

    return list(files_to_store.values())


def get_case_study_file_name_filter(
    case_study: tp.Optional[CaseStudy]
) -> tp.Callable[[str], bool]:
    """
    Generate a case study specific file-name filter function that allows the
    user to check if a file name is related to this case study.

    Returns:
        a filter function that returns ``True`` in cases where a revision of
        file belongs to this case study
    """

    def cs_filter(file_name: str) -> bool:
        """
        Filter files that are not in the case study.

        Returns:
            ``True`` if a case_study is set and the commit_hash of the file
            is not part of this case_study, otherwise, ``False``.
        """
        if case_study is None:
            return False

        return not case_study.has_revision(
            ReportFilename(file_name).commit_hash
        )

    return cs_filter


def get_unique_cs_name(case_studies: tp.List[CaseStudy]) -> tp.List[str]:
    """
    Create a list of unique names for the given case studies.

    If a case studie's project ocurrs only in one case study in the list, choose
    the project name as the name, otherwise, add the case studie's version to
    the name.

    Args:
        case_studies: the list of case studies to generate names for

    Returns:
        a list of unique names for the given case studies in the same order

    Test:
    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("gzip", 1)])
    ['xz', 'gzip']

    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("xz", 2)])
    ['xz_1', 'xz_2']

    Test:
    >>> get_unique_cs_name([CaseStudy("xz", 1), CaseStudy("gzip", 1), \
        CaseStudy("xz", 2)])
    ['xz_1', 'gzip', 'xz_2']
    """
    sorted_cs = sorted(case_studies, key=lambda cs: cs.project_name)
    cs_names = dict(
        (k, list(v)) for k, v in groupby(sorted_cs, lambda cs: cs.project_name)
    )

    return [
        cs.project_name if len(cs_names[cs.project_name]) == 1 else
        f"{cs.project_name}_{cs.version}" for cs in case_studies
    ]


###############################################################################
# Case-study extender
###############################################################################
def extend_with_extra_revs(
    case_study: CaseStudy, cmap: CommitMap, extra_revs: tp.List[str],
    merge_stage: int
) -> None:
    """
    Extend a case_study with extra revisions, specified by the caller with
    kwargs['extra_revs'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        extra_revs: revisions to add to the case_study
        merge_stage: stage to add the new revisions to
    """
    new_rev_items = [(FullCommitHash(rev), idx)
                     for rev, idx in cmap.mapping_items()
                     if any(map(rev.startswith, extra_revs))]

    case_study.include_revisions(new_rev_items, merge_stage, True)


def extend_with_revs_per_year(
    case_study: CaseStudy, cmap: CommitMap, merge_stage: int,
    ignore_blocked: bool, git_path: str, revs_per_year: int, revs_year_sep: bool
) -> None:
    """
    Extend a case_study with ``revs_per_year`` revisions per year.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        merge_stage: stage to add the new revisions to
        ignore_blocked: ignore blocked revisions'
        git_path: git path to the project
        revs_per_year:  revisions to add per year
        revs_year_sep: put revisions in separate stages for each year
    """

    def parse_int_string(string: tp.Optional[str]) -> tp.Optional[int]:
        if string is None:
            return None

        try:
            return int(string)
        except ValueError:
            return None

    def get_or_create_stage_for_year(year: int) -> int:
        stages = case_study.stages
        num_stages = len(stages)

        for stage_index in range(num_stages):
            stage_year = parse_int_string(stages[stage_index].name)

            if stage_year is None:
                continue
            if stage_year == year:
                return stage_index
            if stage_year > year:
                continue
            if stage_year < year:
                case_study.insert_empty_stage(stage_index)
                case_study.name_stage(stage_index, str(year))
                return stage_index

        case_study.insert_empty_stage(num_stages)
        case_study.name_stage(num_stages, str(year))
        return num_stages

    repo = pygit2.Repository(pygit2.discover_repository(git_path))
    last_commit = repo[repo.head.target]

    commits: tp.DefaultDict[int, tp.List[FullCommitHash]] = defaultdict(
        list
    )  # maps year -> list of commits
    for commit in repo.walk(last_commit.id, pygit2.GIT_SORT_TIME):
        commit_date = datetime.utcfromtimestamp(commit.commit_time)
        commits[commit_date.year].append(
            FullCommitHash.from_pygit_commit(commit)
        )

    new_rev_items = []  # new revisions that get added to to case_study
    for year, commits_in_year in commits.items():
        samples = min(len(commits_in_year), revs_per_year)
        sample_commit_indices = sorted(
            random.sample(range(len(commits_in_year)), samples)
        )

        for commit_index in sample_commit_indices:
            commit_hash = commits_in_year[commit_index]
            if ignore_blocked and is_revision_blocked(
                commit_hash.to_short_commit_hash(),
                get_project_cls_by_name(case_study.project_name)
            ):
                continue
            time_id = cmap.time_id(commit_hash)
            new_rev_items.append((commit_hash, time_id))

        if revs_year_sep:
            merge_stage = get_or_create_stage_for_year(year)

        case_study.include_revisions(new_rev_items, merge_stage, True)
        new_rev_items.clear()


def extend_with_distrib_sampling(
    case_study: CaseStudy, cmap: CommitMap,
    sampling_method: NormalSamplingMethod, merge_stage: int, num_rev: int,
    ignore_blocked: bool, only_code_commits: bool
) -> None:
    """
    Extend a case study by sampling 'num_rev' new revisions, according to
    distribution specified with kwargs['distribution'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        sampling_method: distribution to use for sampling
        merge_stage: stage the revisions will be added to
        num_rev: number of revisions to add
        ignore_blocked: ignore_blocked revisions
        only_code_commits: exclude commits which don't change code
    """
    is_blocked: tp.Callable[[ShortCommitHash, tp.Type[Project]],
                            bool] = lambda rev, _: False
    if ignore_blocked:
        is_blocked = is_revision_blocked

    is_code_commit: tp.Callable[[ShortCommitHash], bool] = lambda rev: True
    if only_code_commits:
        churn_conf = ChurnConfig.create_c_style_languages_config()
        project_git_path = get_local_project_git_path(case_study.project_name)

        def is_c_cpp_code_commit(commit: ShortCommitHash) -> bool:
            return contains_source_code(commit, project_git_path, churn_conf)

        is_code_commit = is_c_cpp_code_commit

    # Needs to be sorted so the propability distribution over the length
    # of the list is the same as the distribution over the commits age history
    project_cls = get_project_cls_by_name(case_study.project_name)
    revision_list = [
        (FullCommitHash(rev), idx)
        for rev, idx in sorted(list(cmap.mapping_items()), key=lambda x: x[1])
        if
        not case_study.has_revision_in_stage(ShortCommitHash(rev), merge_stage)
        and not is_blocked(ShortCommitHash(rev), project_cls) and
        is_code_commit(ShortCommitHash(rev))
    ]

    case_study.include_revisions(
        sampling_method.sample_n(revision_list, num_rev), merge_stage
    )


def extend_with_smooth_revs(
    case_study: CaseStudy, cmap: CommitMap, boundary_gradient: int,
    ignore_blocked: bool, plot: Plot, merge_stage: int
) -> None:
    """
    Extend a case study with extra revisions that could smooth plot curves. This
    can remove steep gradients that result from missing certain revisions when
    sampling.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        ignore_blocked: ignore_blocked revisions
        merge_stage: stage the revisions will be added to
        plot: Plot to calculate new revisions from.
        boundary_gradient: Maximal expected gradient in percent between
            two revisions
    """
    # convert input to float %
    gradient = boundary_gradient / float(100)
    print("Using boundary gradient: ", gradient)
    new_revisions = plot.calc_missing_revisions(gradient)

    if ignore_blocked:
        new_revisions = set(
            filter_blocked_revisions(
                list(new_revisions),
                get_project_cls_by_name(case_study.project_name)
            )
        )

    # Remove revision that are already present in another stage.
    new_revisions = {
        rev for rev in new_revisions if not case_study.has_revision(rev)
    }
    if new_revisions:
        print("Found new revisions: ", new_revisions)
        case_study.include_revisions([
            (rev, cmap.time_id(rev)) for rev in new_revisions
        ], merge_stage)
    else:
        print(
            "No new revisions found that where not already "
            "present in the case study."
        )


def extend_with_release_revs(
    case_study: CaseStudy, cmap: CommitMap, release_type: ReleaseType,
    ignore_blocked: bool, merge_stage: int
) -> None:
    """
    Extend a case study with revisions marked as a release. This extender relies
    on the project to determine appropriate revisions.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        ignore_blocked: ignore_blocked revisions
        merge_stage: stage the revisions will be added to
        release_type: release type to add
    """
    project_cls: tp.Type[Project] = get_project_cls_by_name(
        case_study.project_name
    )
    release_provider = ReleaseProvider.get_provider_for_project(project_cls)
    release_revisions: tp.List[FullCommitHash] = [
        revision for revision, release in
        release_provider.get_release_revisions(release_type)
    ]

    if ignore_blocked:
        release_revisions = filter_blocked_revisions(
            release_revisions, project_cls
        )

    case_study.include_revisions([
        (rev, cmap.time_id(rev)) for rev in release_revisions
    ], merge_stage)


def extend_with_bug_commits(
    case_study: CaseStudy, cmap: CommitMap, report_type: tp.Type['BaseReport'],
    merge_stage: int, ignore_blocked: bool
) -> None:
    """
    Extend a case study with revisions that either introduced or fixed a bug as
    determined by the given SZZ tool.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        ignore_blocked: ignore_blocked revisions
        merge_stage: stage the revisions will be added to
        report_type: report to use for bug detection
    """
    project_cls: tp.Type[Project] = get_project_cls_by_name(
        case_study.project_name
    )

    def load_bugs_from_szz_report(
        load_fun: tp.Callable[[Path], SZZReport]
    ) -> tp.Optional[tp.FrozenSet[RawBug]]:
        reports = get_processed_revisions_files(
            case_study.project_name, report_type
        )
        if not reports:
            LOG.warning(
                f"I could not find any {report_type} reports. "
                "Falling back to bug provider."
            )
            return None
        report = load_fun(reports[0])
        return report.get_all_raw_bugs()

    bugs: tp.Optional[tp.FrozenSet[RawBug]] = None
    if report_type == SZZUnleashedReport:
        bugs = load_bugs_from_szz_report(load_szzunleashed_report)
    elif report_type == PyDrillerSZZReport:
        bugs = load_bugs_from_szz_report(load_pydriller_szz_report)
    else:
        LOG.warning(
            f"Report type {report_type} is not supported by this extender "
            f"strategy. Falling back to bug provider."
        )

    if bugs is None:
        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(case_study.project_name)
        )
        bugs = bug_provider.find_raw_bugs()

    revisions: tp.Set[FullCommitHash] = set()
    for bug in bugs:
        revisions.add(bug.fixing_commit)
        revisions.update(bug.introducing_commits)

    rev_list = list(revisions)
    if ignore_blocked:
        rev_list = filter_blocked_revisions(rev_list, project_cls)

    case_study.include_revisions([(rev, cmap.time_id(rev)) for rev in rev_list],
                                 merge_stage)

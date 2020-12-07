"""A case study is used to pin down the exact set of revisions that should be
analysed for a project."""
import random
import typing as tp
from collections import defaultdict
from datetime import datetime
from enum import Enum
from itertools import groupby
from pathlib import Path

import pygit2
from benchbuild import Project  # type: ignore

from varats.base.sampling_method import (
    NormalSamplingMethod,
    UniformSamplingMethod,
    HalfNormalSamplingMethod,
)
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.plot.plot_utils import check_required_args
from varats.plot.plots import PlotRegistry
from varats.project.project_util import get_project_cls_by_name
from varats.provider.release.release_provider import ReleaseProvider
from varats.report.report import FileStatusExtension, MetaReport
from varats.revision.revisions import (
    get_failed_revisions,
    get_processed_revisions,
    get_tagged_revision,
    get_tagged_revisions,
    filter_blocked_revisions,
    is_revision_blocked,
)


class ExtenderStrategy(Enum):
    """Enum for all currently supported extender strategies."""
    value: int

    mixed = -1
    simple_add = 1
    distrib_add = 2
    smooth_plot = 3
    per_year_add = 4
    release_add = 5


def processed_revisions_for_case_study(
    case_study: CaseStudy, result_file_type: MetaReport
) -> tp.List[str]:
    """
    Computes all revisions of this case study that have been processed.

    Args:
        case_study: to work on
        result_file_type: report type of the result files

    Returns:
        a list of processed revisions
    """
    total_processed_revisions = set(
        get_processed_revisions(case_study.project_name, result_file_type)
    )

    return [
        rev for rev in case_study.revisions
        if rev[:10] in total_processed_revisions
    ]


def failed_revisions_for_case_study(
    case_study: CaseStudy, result_file_type: MetaReport
) -> tp.List[str]:
    """
    Computes all revisions of this case study that have failed.

    Args:
        case_study: to work on
        result_file_type: report type of the result files

    Returns:
        a list of failed revisions
    """
    total_failed_revisions = set(
        get_failed_revisions(case_study.project_name, result_file_type)
    )

    return [
        rev for rev in case_study.revisions
        if rev[:10] in total_failed_revisions
    ]


def get_revisions_status_for_case_study(
    case_study: CaseStudy,
    result_file_type: MetaReport,
    stage_num: int = -1,
    tag_blocked: bool = True
) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
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
    project_cls = get_project_cls_by_name(case_study.project_name)
    tagged_revisions = get_tagged_revisions(
        project_cls, result_file_type, tag_blocked
    )

    def filtered_tagged_revs(
        rev_provider: tp.Iterable[str]
    ) -> tp.List[tp.Tuple[str, FileStatusExtension]]:
        filtered_revisions = []
        for rev in rev_provider:
            found = False
            short_rev = rev[:10]
            for tagged_rev in tagged_revisions:
                if short_rev == tagged_rev[0][:10]:
                    filtered_revisions.append(tagged_rev)
                    found = True
                    break
            if not found:
                if tag_blocked and is_revision_blocked(short_rev, project_cls):
                    filtered_revisions.append(
                        (short_rev, FileStatusExtension.Blocked)
                    )
                else:
                    filtered_revisions.append(
                        (short_rev, FileStatusExtension.Missing)
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
    revision: str,
    result_file_type: MetaReport,
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
    case_study: CaseStudy, result_dir: Path, report_type: MetaReport
) -> tp.List[Path]:
    """
    Return all result files of a specific type that belong to a given case
    study. For revision with multiple files, the newest file will be selected.

    Returns:
        list of result file paths
    """
    files_to_store: tp.Dict[str, Path] = dict()

    result_dir /= case_study.project_name
    if not result_dir.exists():
        return []

    for opt_res_file in result_dir.iterdir():
        if report_type.is_correct_report_type(opt_res_file.name):
            commit_hash = report_type.get_commit_hash_from_result_file(
                opt_res_file.name
            )
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

        commit_hash = MetaReport.get_commit_hash_from_result_file(file_name)
        return not case_study.has_revision(commit_hash)

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
# Case-study generation
###############################################################################


@check_required_args(['extra_revs', 'git_path'])
def generate_case_study(
    sampling_method: NormalSamplingMethod, cmap: CommitMap,
    case_study_version: int, project_name: str, **kwargs: tp.Any
) -> CaseStudy:
    """
    Generate a case study for a given project.

    This function will draw `num_samples` revisions from the history of the
    given project and persists the selected set into a case study for
    evaluation.

    Args:
        sampling_method: to use for revision sampling
        cmap: commit map to map revisions to unique IDs
        case_study_version: version to set for the case study
        project_name: name of the project so sample from
        kwargs: additional args that should be passed on to the strategy

    Returns:
        a new case study
    """
    case_study = CaseStudy(project_name, case_study_version)

    if kwargs['revs_per_year'] > 0:
        extend_with_revs_per_year(case_study, cmap, **kwargs)

    if (
        isinstance(
            sampling_method, (HalfNormalSamplingMethod, UniformSamplingMethod)
        )
    ):
        extend_with_distrib_sampling(case_study, cmap, **kwargs)

    if kwargs['extra_revs']:
        extend_with_extra_revs(case_study, cmap, **kwargs)

    return case_study


###############################################################################
# Case-study extender
###############################################################################


def extend_case_study(
    case_study: CaseStudy, cmap: CommitMap, ext_strategy: ExtenderStrategy,
    **kwargs: tp.Any
) -> None:
    """
    Extend a case study inplace with new revisions according to the specified
    extender strategy.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
        ext_strategy: determines how the case study should be extended
    """

    if ext_strategy is ExtenderStrategy.simple_add:
        extend_with_extra_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.distrib_add:
        extend_with_distrib_sampling(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.smooth_plot:
        extend_with_smooth_revs(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.per_year_add:
        extend_with_revs_per_year(case_study, cmap, **kwargs)
    elif ext_strategy is ExtenderStrategy.release_add:
        extend_with_release_revs(case_study, cmap, **kwargs)


@check_required_args(['extra_revs', 'merge_stage'])
def extend_with_extra_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case_study with extra revisions, specified by the caller with
    kwargs['extra_revs'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    extra_revs = kwargs['extra_revs']
    merge_stage = kwargs['merge_stage']

    new_rev_items = [
        rev_item for rev_item in cmap.mapping_items()
        if any(map(rev_item[0].startswith, extra_revs))
    ]

    case_study.include_revisions(new_rev_items, merge_stage, True)


@check_required_args([
    'git_path', 'revs_per_year', 'merge_stage', 'revs_year_sep'
])
def extend_with_revs_per_year(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case_study with ``n`` revisions per year, specifed by the caller
    with kwargs['revs_per_year'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
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

    repo = pygit2.Repository(pygit2.discover_repository(kwargs['git_path']))
    last_commit = repo[repo.head.target]
    revs_year_sep = kwargs['revs_year_sep']

    commits: tp.DefaultDict[int, tp.List[str]] = defaultdict(
        list
    )  # maps year -> list of commits
    for commit in repo.walk(last_commit.id, pygit2.GIT_SORT_TIME):
        commit_date = datetime.utcfromtimestamp(commit.commit_time)
        commits[commit_date.year].append(str(commit.id))

    new_rev_items = []  # new revisions that get added to to case_study
    project_cls = get_project_cls_by_name(case_study.project_name)
    for year, commits_in_year in commits.items():
        samples = min(len(commits_in_year), kwargs['revs_per_year'])
        sample_commit_indices = sorted(
            random.sample(range(len(commits_in_year)), samples)
        )

        for commit_index in sample_commit_indices:
            commit_hash = commits_in_year[commit_index]
            if kwargs["ignore_blocked"] and is_revision_blocked(
                commit_hash, project_cls
            ):
                continue
            time_id = cmap.time_id(commit_hash)
            new_rev_items.append((commit_hash, time_id))

        if revs_year_sep:
            stage_index = get_or_create_stage_for_year(year)
        else:
            stage_index = kwargs['merge_stage']

        case_study.include_revisions(new_rev_items, stage_index, True)
        new_rev_items.clear()


@check_required_args(['distribution', 'merge_stage', 'num_rev'])
def extend_with_distrib_sampling(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study by sampling 'num_rev' new revisions, according to
    distribution specified with kwargs['distribution'].

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    is_blocked: tp.Callable[[str, tp.Type[tp.Any]], bool] = lambda rev, _: False
    if kwargs["ignore_blocked"]:
        is_blocked = is_revision_blocked

    # Needs to be sorted so the propability distribution over the length
    # of the list is the same as the distribution over the commits age history
    project_cls = get_project_cls_by_name(case_study.project_name)
    revision_list = [
        rev_item
        for rev_item in sorted(list(cmap.mapping_items()), key=lambda x: x[1])
        if not case_study.
        has_revision_in_stage(rev_item[0], kwargs['merge_stage']) and
        not is_blocked(rev_item[0], project_cls)
    ]

    sampling_method = kwargs['distribution']

    case_study.include_revisions(
        sampling_method.sample_n(revision_list, kwargs['num_rev']),
        kwargs['merge_stage'],
        sampling_method=kwargs['distribution']
    )


@check_required_args(['plot_type', 'boundary_gradient'])
def extend_with_smooth_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study with extra revisions that could smooth plot curves. This
    can remove steep gradients that result from missing certain revisions when
    sampling.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    kwargs['plot_case_study'] = case_study
    kwargs['cmap'] = cmap
    plot = plot_type(**kwargs)
    # convert input to float %
    boundary_gradient = kwargs['boundary_gradient'] / float(100)
    print("Using boundary gradient: ", boundary_gradient)
    new_revisions = plot.calc_missing_revisions(boundary_gradient)

    if kwargs["ignore_blocked"]:
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
        ], kwargs['merge_stage'])
    else:
        print(
            "No new revisions found that where not already "
            "present in the case study."
        )


@check_required_args(['project', 'release_type', 'merge_stage'])
def extend_with_release_revs(
    case_study: CaseStudy, cmap: CommitMap, **kwargs: tp.Any
) -> None:
    """
    Extend a case study with revisions marked as a release. This extender relies
    on the project to determine appropriate revisions.

    Args:
        case_study: to extend
        cmap: commit map to map revisions to unique IDs
    """
    project_cls: tp.Type[Project] = get_project_cls_by_name(kwargs['project'])
    release_provider = ReleaseProvider.get_provider_for_project(project_cls)
    release_revisions: tp.List[str] = [
        revision for revision, release in
        release_provider.get_release_revisions(kwargs['release_type'])
    ]

    if kwargs["ignore_blocked"]:
        release_revisions = filter_blocked_revisions(
            release_revisions, project_cls
        )

    case_study.include_revisions([
        (rev, cmap.time_id(rev)) for rev in release_revisions
    ],
                                 kwargs['merge_stage'],
                                 release_type=kwargs['release_type'])

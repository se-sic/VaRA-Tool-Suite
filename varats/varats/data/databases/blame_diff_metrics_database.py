"""Module for diff based commit-data metrics."""
import typing as tp
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_report import (
    BlameReport,
    BlameReportDiff,
    generate_degree_tuples,
    generate_author_degree_tuples,
    generate_avg_time_distribution_tuples,
    generate_max_time_distribution_tuples,
    count_interactions,
    count_interacting_commits,
    count_interacting_authors,
)
from varats.jupyterhelper.file import load_blame_report
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import get_local_project_git
from varats.report.report import ReportFilename
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
    get_processed_revisions,
)
from varats.utils.git_util import (
    ChurnConfig,
    calc_code_churn,
    create_commit_lookup_helper,
    ShortCommitHash,
    FullCommitHash,
)


def id_from_paths(paths: tp.Tuple[Path, Path]) -> str:
    """
    Concatenates the commit hashes of two result files separated by an
    underscore.

    Args:
        paths: the path tuple of the result file paths

    Returns:
        the combined commit hash string of the result files
    """

    return \
        f"{ReportFilename(paths[0]).commit_hash}_" \
        f"{ReportFilename(paths[1]).commit_hash}"


def timestamp_from_paths(paths: tp.Tuple[Path, Path]) -> str:
    """
    Concatenates the timestamp of two result files separated by an underscore.

    Args:
        paths: the path tuple of the result file paths

    Returns:
        the combined timestamp string of the result files
    """
    return f"{paths[0].stat().st_mtime_ns}_{paths[1].stat().st_mtime_ns}"


def compare_timestamps(ts1: str, ts2: str) -> bool:
    """
    Compares the timestamp of two combined timestamp strings and determines if
    the first one is newer than the second one.

    Args:
        ts1: the first combined timestamp string
        ts2: the second combined timestamp string

    Returns: True if ``ts1`` is newer than ``ts2``
    """
    ts1_head, ts1_pred = ts1.split("_")
    ts2_head, ts2_pred = ts2.split("_")
    return int(ts1_head) > int(ts2_head) or int(ts1_pred) > int(ts2_pred)


def build_report_files_tuple(
    project_name: str, case_study: tp.Optional[CaseStudy]
) -> tp.Tuple[tp.Dict[ShortCommitHash, Path], tp.Dict[ShortCommitHash, Path]]:
    """
    Build the mappings between commit hash to its corresponding report file
    path, where the first mapping corresponds to commit hashes and their
    successful report files and the second mapping to commit hashes and their
    failed report files.

    Args:
        project_name: the name of the project
        case_study: the selected CaseStudy

    Returns:
        the mappings from commit hash to successful and failed report files as
        tuple
    """
    report_files: tp.Dict[ShortCommitHash, Path] = {
        ReportFilename(report).commit_hash: report
        for report in get_processed_revisions_files(
            project_name,
            BlameReport,
            get_case_study_file_name_filter(case_study)
            if case_study else lambda x: False,
        )
    }

    failed_report_files: tp.Dict[ShortCommitHash, Path] = {
        ReportFilename(report).commit_hash: report
        for report in get_failed_revisions_files(
            project_name,
            BlameReport,
            get_case_study_file_name_filter(case_study)
            if case_study else lambda x: False,
        )
    }
    return report_files, failed_report_files


ReportPairTupleList = tp.List[tp.Tuple[Path, Path]]


def build_report_pairs_tuple(
    project_name: str, commit_map: CommitMap, case_study: tp.Optional[CaseStudy]
) -> tp.Tuple[ReportPairTupleList, ReportPairTupleList]:
    """
    Builds a tuple of tuples (ReportPairTupleList, ReportPairTupleList) of
    successful report files with their corresponding predecessors and tuples of
    failed report files with their corresponding predecessor.

    Args:
        project_name: the name of the project
        commit_map: the selected CommitMap
        case_study: the selected CaseStudy

    Returns:
        the tuple of report file to predecessor tuples for all successful and
        failed reports
    """

    report_files, failed_report_files = build_report_files_tuple(
        project_name, case_study
    )

    sampled_revs: tp.List[ShortCommitHash]
    if case_study:
        sampled_revs = [
            rev.to_short_commit_hash() for rev in case_study.revisions
        ]
    else:
        sampled_revs = get_processed_revisions(project_name, BlameReport)
    short_time_id_cache: tp.Dict[ShortCommitHash, int] = {
        rev: commit_map.short_time_id(rev) for rev in sampled_revs
    }

    report_pairs: tp.List[tp.Tuple[Path, Path]] = [
        (report, pred) for report, pred in [(
            report_file,
            get_predecessor_report_file(
                c_hash, commit_map, short_time_id_cache, report_files,
                sampled_revs
            )
        ) for c_hash, report_file in report_files.items()] if pred is not None
    ]

    failed_report_pairs: tp.List[tp.Tuple[Path, Path]] = [
        (report, pred) for report, pred in chain.from_iterable(
            [[(
                report_file,
                get_predecessor_report_file(
                    c_hash, commit_map, short_time_id_cache, report_files,
                    sampled_revs
                )
            ),
              (
                  get_successor_report_file(
                      c_hash, commit_map, short_time_id_cache, report_files,
                      sampled_revs
                  ), report_file
              )] for c_hash, report_file in failed_report_files.items()]
        ) if report is not None and pred is not None
    ]
    return report_pairs, failed_report_pairs


def get_predecessor_report_file(
    c_hash: ShortCommitHash, commit_map: CommitMap,
    short_time_id_cache: tp.Dict[ShortCommitHash, int],
    report_files: tp.Dict[ShortCommitHash,
                          Path], sampled_revs: tp.List[ShortCommitHash]
) -> tp.Optional[Path]:
    """
    Finds the preceding report file of the report that corresponds to the passed
    commit hash within the sampled revisions of the passed report files.

    Args:
        c_hash: the selected commit hash
        commit_map: the selected CommitMap
        short_time_id_cache: the short time id cache
        report_files: the report files
        sampled_revs: the sampled revisions

    Returns:
        the path to the preceding report file if it exists
    """
    commit_time_id = commit_map.short_time_id(c_hash)
    pred_commits = [(short_time_id_cache[rev], rev)
                    for rev in sampled_revs
                    if short_time_id_cache[rev] < commit_time_id]

    if not pred_commits:
        return None

    pred_report_commit_hash = max(pred_commits, key=lambda x: x[0])[1]
    return report_files.get(pred_report_commit_hash, None)


def get_successor_report_file(
    c_hash: ShortCommitHash, commit_map: CommitMap,
    short_time_id_cache: tp.Dict[ShortCommitHash, int],
    report_files: tp.Dict[ShortCommitHash,
                          Path], sampled_revs: tp.List[ShortCommitHash]
) -> tp.Optional[Path]:
    """
    Finds the subsequent report file of the report that corresponds to the
    passed commit hash within the sampled revisions of the passed report files.

    Args:
        c_hash: the selected commit hash
        commit_map: the selected CommitMap
        short_time_id_cache: the short time id cache
        report_files: the report files
        sampled_revs: the sampled revisions

    Returns:
        the path to the subsequent report file if it exists
    """

    commit_time_id = commit_map.short_time_id(c_hash)
    succ_commits = [(short_time_id_cache[rev], rev)
                    for rev in sampled_revs
                    if short_time_id_cache[rev] > commit_time_id]

    if not succ_commits:
        return None

    succ_report_commit_hash = min(succ_commits, key=lambda x: x[0])[1]
    return report_files.get(succ_report_commit_hash, None)


class BlameDiffMetrics(Enum):
    """Blame interaction metrics."""
    value: tp.Tuple[str, str]  # pylint: disable=invalid-name

    CHURN = ("churn", 'int64')
    NUM_INTERACTIONS = ("num_interactions", 'int64')
    NUM_INTERACTING_COMMITS = ("num_interacting_commits", 'int64')
    NUM_INTERACTING_AUTHORS = ("num_interacting_authors", 'int64')
    CI_DEGREE_MEAN = ("ci_degree_mean", 'int')
    AUTHOR_MEAN = ("author_mean", 'int')
    AVG_TIME_MEAN = ("avg_time_mean", 'int')
    CI_DEGREE_MAX = ("ci_degree_max", 'int')
    AUTHOR_MAX = ("author_max", 'int')
    AVG_TIME_MAX = ("avg_time_max", 'int')
    YEAR = ("year", 'int64')

    @staticmethod
    def to_str_dict() -> tp.Dict[str, str]:
        return {metric.value[0]: metric.value[1] for metric in BlameDiffMetrics}


class BlameDiffMetricsDatabase(
    EvaluationDatabase,
    cache_id="blame_diff_metrics_data",
    column_types=BlameDiffMetrics.to_str_dict()
):
    """Metrics database that contains all different blame-interaction metrics
    that are based on a diff between two `BlameReports`."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        repo = get_local_project_git(project_name)
        commit_lookup = create_commit_lookup_helper(project_name)

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_report(
            report_paths: tp.Tuple[Path, Path]
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            # Look-up commit and infos about the HEAD commit of the report
            head_report = load_blame_report(report_paths[0])
            pred_report = load_blame_report(report_paths[1])
            commit = repo.get(head_report.head_commit.hash)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)
            pred_commit = repo.get(pred_report.head_commit.hash)

            diff_between_head_pred = BlameReportDiff(head_report, pred_report)

            # Calculate the total churn between pred and base commit
            code_churn = calc_code_churn(
                Path(repo.path), FullCommitHash.from_pygit_commit(pred_commit),
                FullCommitHash.from_pygit_commit(commit),
                ChurnConfig.create_c_style_languages_config()
            )
            total_churn = code_churn[1] + code_churn[2]

            def weighted_avg(tuples: tp.List[tp.Tuple[int, int]]) -> float:
                total_sum = 0
                degree_sum = 0
                for degree, amount in tuples:
                    degree_sum += degree
                    total_sum += (degree * amount)

                return total_sum / max(1, degree_sum)

            def combine_max(tuples: tp.List[tp.Tuple[int, int]]) -> float:
                if tuples:
                    return max([x for x, y in tuples])
                return 0

            return (
                pd.DataFrame({
                    'revision':
                        head_report.head_commit.hash,
                    'time_id':
                        commit_map.short_time_id(head_report.head_commit),
                    'churn':
                        total_churn,
                    'num_interactions':
                        count_interactions(diff_between_head_pred),
                    'num_interacting_commits':
                        count_interacting_commits(diff_between_head_pred),
                    'num_interacting_authors':
                        count_interacting_authors(
                            diff_between_head_pred, commit_lookup
                        ),
                    "ci_degree_mean":
                        weighted_avg(
                            generate_degree_tuples(diff_between_head_pred)
                        ),
                    "author_mean":
                        weighted_avg(
                            generate_author_degree_tuples(
                                diff_between_head_pred, commit_lookup
                            )
                        ),
                    "avg_time_mean":
                        weighted_avg(
                            generate_avg_time_distribution_tuples(
                                diff_between_head_pred, commit_lookup, 1
                            )
                        ),
                    "ci_degree_max":
                        combine_max(
                            generate_degree_tuples(diff_between_head_pred)
                        ),
                    "author_max":
                        combine_max(
                            generate_author_degree_tuples(
                                diff_between_head_pred, commit_lookup
                            )
                        ),
                    "avg_time_max":
                        combine_max(
                            generate_max_time_distribution_tuples(
                                diff_between_head_pred, commit_lookup, 1
                            )
                        ),
                    'year':
                        commit_date.year,
                },
                             index=[0]), id_from_paths(report_paths),
                timestamp_from_paths(report_paths)
            )

        report_pairs, failed_report_pairs = build_report_pairs_tuple(
            project_name, commit_map, case_study
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_pairs, failed_report_pairs,
            create_dataframe_layout, create_data_frame_for_report,
            id_from_paths, timestamp_from_paths, compare_timestamps
        )

        return data_frame

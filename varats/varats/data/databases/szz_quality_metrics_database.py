"""Module for SZZ quality metrics data."""
import logging
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.blame_diff_metrics_database import (
    id_from_paths,
    timestamp_from_paths,
    compare_timestamps,
)
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_report import (
    BlameReport,
    get_interacting_commits_for_commit,
)
from varats.data.reports.szz_report import (
    SZZReport,
    SZZUnleashedReport,
    PyDrillerSZZReport,
)
from varats.jupyterhelper.file import load_blame_report
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.project.project_util import get_primary_project_source
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    ShortCommitHash,
    FullCommitHash,
)

LOG = logging.getLogger(__name__)


def _get_requested_report_paths(
    project_name: str, szz_report: SZZReport
) -> tp.Dict[ShortCommitHash, Path]:
    bugs = szz_report.get_all_raw_bugs()
    requested_report_revisions: tp.Set[ShortCommitHash] = set()
    for bug in bugs:
        requested_report_revisions.add(bug.fixing_commit.to_short_commit_hash())
        requested_report_revisions.update(
            introducer.to_short_commit_hash()
            for introducer in bug.introducing_commits
        )

    report_map: tp.Dict[ShortCommitHash, Path] = {}
    for report_path in get_processed_revisions_files(project_name, BlameReport):
        report_revision = ReportFilename(report_path).commit_hash
        if report_revision in requested_report_revisions:
            report_map[report_revision] = report_path

    return report_map


def _calculate_szz_quality_score(
    fix_in: tp.Set[CommitRepoPair], fix_out: tp.Set[CommitRepoPair],
    intro_in: tp.Set[CommitRepoPair], intro_out: tp.Set[CommitRepoPair]
) -> float:
    """
    Calculates a quality score that estimates how likely it is that a commit
    introduced a bug that is fixed in another commit.

    The score is calculated by computing how well the commit interactions
    surrounding the fix match the commit interactions surrounding the
    introducer. The underlying assumption is that if the data-flows (and hence,
    the interactions) changed a lot between these commits, then it is likely
    that the bug was introduced at a later point in time. Hence, the higher the
    score, the more likely it is that the introducer was identified correctly.
    The score is calculated as the fraction of changed commit interactions.
    Incoming and outgoing interactions are viewed separately and combined via
    weighted average.

    Args:
        fix_in: incoming interactions of the fixing commit
        fix_out: outgoing interactions of the fixing commit
        intro_in: incoming interactions of the introducing commit
        intro_out: outgoing interactions of the introcucing commit

    Returns:
        a score estimating how likely it is that the introducer is correct
    """
    in_all = len(fix_in.union(intro_in))
    in_diff = len(fix_in.symmetric_difference(intro_in))
    in_frac = in_diff / in_all if in_all else 0
    out_all = len(fix_out.union(intro_out))
    out_diff = len(fix_out.symmetric_difference(intro_out))
    out_frac = out_diff / out_all if out_all else 0
    total = in_all + out_all
    score: float
    if len(fix_in) + len(fix_out) == 0 or len(intro_in) + len(intro_out) == 0:
        score = -1
    else:
        score = 1 - in_frac * (in_all / total) - out_frac * (out_all / total)
    return score


def _load_dataframe_for_report(
    project_name: str, cache_id: str, columns: tp.List[str],
    commit_map: CommitMap, szz_report: SZZReport
) -> pd.DataFrame:
    commit_lookup = create_commit_lookup_helper(project_name)
    commit_map = get_commit_map(project_name)
    prj_src = get_primary_project_source(project_name)

    def create_dataframe_layout() -> pd.DataFrame:
        df_layout = pd.DataFrame(columns=columns)
        return df_layout

    def create_data_frame_for_report(
        report_paths: tp.Tuple[Path, Path]
    ) -> tp.Tuple[pd.DataFrame, str, str]:
        # Look-up commit and infos about the HEAD commit of the report
        fix_report = load_blame_report(report_paths[0])
        intro_report = load_blame_report(report_paths[1])
        fix_commit = commit_lookup(
            CommitRepoPair(
                commit_map.convert_to_full_or_warn(fix_report.head_commit),
                prj_src.local
            )
        )
        intro_commit = commit_lookup(
            CommitRepoPair(
                commit_map.convert_to_full_or_warn(intro_report.head_commit),
                prj_src.local
            )
        )

        fix_in, fix_out = get_interacting_commits_for_commit(
            fix_report,
            CommitRepoPair(
                FullCommitHash.from_pygit_commit(fix_commit), prj_src.local
            )
        )
        intro_in, intro_out = get_interacting_commits_for_commit(
            intro_report,
            CommitRepoPair(
                FullCommitHash.from_pygit_commit(intro_commit), prj_src.local
            )
        )

        score = _calculate_szz_quality_score(
            fix_in, fix_out, intro_in, intro_out
        )

        return (
            pd.DataFrame({
                'revision': str(fix_report.head_commit),
                'time_id': commit_map.short_time_id(fix_report.head_commit),
                'introducer': str(intro_report.head_commit),
                'score': score
            },
                         index=[0]), id_from_paths(report_paths),
            timestamp_from_paths(report_paths)
        )

    report_map = _get_requested_report_paths(project_name, szz_report)
    available_revisions = report_map.keys()

    new_entries: tp.List[tp.Tuple[Path, Path]] = []
    remove_entries: tp.List[tp.Tuple[Path, Path]] = []
    bugs = szz_report.get_all_raw_bugs()
    for bug in bugs:
        fix = bug.fixing_commit.to_short_commit_hash()
        if fix in available_revisions:
            for introducer in bug.introducing_commits:
                intro = introducer.to_short_commit_hash()
                if intro in available_revisions:
                    new_entries.append((report_map[fix], report_map[intro]))

    # cls.CACHE_ID is set by superclass
    # pylint: disable=E1101
    data_frame = build_cached_report_table(
        cache_id, project_name, new_entries, remove_entries,
        create_dataframe_layout, create_data_frame_for_report, id_from_paths,
        timestamp_from_paths, compare_timestamps
    )

    return data_frame


class SZZUnleashedQualityMetricsDatabase(
    EvaluationDatabase,
    cache_id="szz_unleashed_quality_metrics",
    column_types={
        "introducer": 'str',
        "score": 'int64'
    }
):
    """SZZ quality metrics database for SZZUnleashed data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        report_paths = get_processed_revisions_files(
            project_name, SZZUnleashedReport
        )
        return _load_dataframe_for_report(
            project_name, cls.CACHE_ID, cls.COLUMNS, commit_map,
            SZZUnleashedReport(report_paths[0])
        )


class PyDrillerSZZQualityMetricsDatabase(
    EvaluationDatabase,
    cache_id="pydriller_szz_quality_metrics",
    column_types={
        "introducer": 'str',
        "score": 'int64'
    }
):
    """SZZ quality metrics database for PyDriller based SZZ data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        report_paths = get_processed_revisions_files(
            project_name, PyDrillerSZZReport
        )
        return _load_dataframe_for_report(
            project_name, cls.CACHE_ID, cls.COLUMNS, commit_map,
            PyDrillerSZZReport(report_paths[0])
        )

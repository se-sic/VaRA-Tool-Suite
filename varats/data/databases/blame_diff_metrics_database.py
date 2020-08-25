"""Module for diff based commit-data metrics."""
import typing as tp
from datetime import datetime
from itertools import chain
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
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
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
    get_processed_revisions,
)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter
from varats.utils.git_util import ChurnConfig, calc_code_churn
from varats.utils.project_util import get_local_project_git


class BlameDiffMetricsDatabase(
    EvaluationDatabase,
    cache_id="blame_diff_metrics_data",
    columns=[
        "churn", "num_interactions", "num_interacting_commits",
        "num_interacting_authors", "ci_degree_mean", "author_mean",
        "avg_time_mean", "ci_degree_max", "author_max", "avg_time_max", "year"
    ]
):
    """Metrics database that contains all different blame-interaction metrics
    that are based on a diff between two `BlameReports`."""

    @staticmethod
    def _id_from_paths(paths: tp.Tuple[Path, Path]) -> str:
        return \
            f"{MetaReport.get_commit_hash_from_result_file(paths[0].name)}_" \
               f"{MetaReport.get_commit_hash_from_result_file(paths[1].name)}"

    @staticmethod
    def _timestamp_from_paths(paths: tp.Tuple[Path, Path]) -> str:
        return f"{paths[0].stat().st_mtime_ns}_{paths[1].stat().st_mtime_ns}"

    @staticmethod
    def _compare_timestamps(ts1: str, ts2: str) -> bool:
        ts1_head, ts1_pred = ts1.split("_")
        ts2_head, ts2_pred = ts2.split("_")
        return int(ts1_head) > int(ts2_head) or int(ts1_pred) > int(ts2_pred)

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.churn = df_layout.churn.astype('int64')
            df_layout.num_interactions = \
                df_layout.num_interactions.astype('int64')
            df_layout.num_interacting_commits = \
                df_layout.num_interacting_commits.astype('int64')
            df_layout.num_interacting_authors = \
                df_layout.num_interacting_authors.astype('int64')
            df_layout.year = df_layout.year.astype('int64')
            return df_layout

        def create_data_frame_for_report(
            report_paths: tp.Tuple[Path, Path]
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            # Look-up commit and infos about the HEAD commit of the report
            head_report = load_blame_report(report_paths[0])
            pred_report = load_blame_report(report_paths[1])
            repo = get_local_project_git(project_name)
            commit = repo.get(head_report.head_commit)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)

            diff_between_head_pred = BlameReportDiff(head_report, pred_report)

            # Calculate the total churn between pred and base commit
            code_churn = calc_code_churn(
                repo, repo.get(pred_report.head_commit), commit,
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
                        head_report.head_commit,
                    'churn':
                        total_churn,
                    'num_interactions':
                        count_interactions(diff_between_head_pred),
                    'num_interacting_commits':
                        count_interacting_commits(diff_between_head_pred),
                    'num_interacting_authors':
                        count_interacting_authors(
                            diff_between_head_pred, project_name
                        ),
                    "ci_degree_mean":
                        weighted_avg(
                            generate_degree_tuples(diff_between_head_pred)
                        ),
                    "author_mean":
                        weighted_avg(
                            generate_author_degree_tuples(
                                diff_between_head_pred, project_name
                            )
                        ),
                    "avg_time_mean":
                        weighted_avg(
                            generate_avg_time_distribution_tuples(
                                diff_between_head_pred, project_name, 1
                            )
                        ),
                    "ci_degree_max":
                        combine_max(
                            generate_degree_tuples(diff_between_head_pred)
                        ),
                    "author_max":
                        combine_max(
                            generate_author_degree_tuples(
                                diff_between_head_pred, project_name
                            )
                        ),
                    "avg_time_max":
                        combine_max(
                            generate_max_time_distribution_tuples(
                                diff_between_head_pred, project_name, 1
                            )
                        ),
                    'year':
                        commit_date.year,
                },
                             index=[0]),
                BlameDiffMetricsDatabase._id_from_paths(report_paths),
                BlameDiffMetricsDatabase._timestamp_from_paths(report_paths)
            )

        def get_predecessor_report_file(c_hash: str) -> tp.Optional[Path]:
            commit_time_id = commit_map.short_time_id(c_hash)
            pred_commits = [(short_time_id_cache[rev], rev)
                            for rev in sampled_revs
                            if short_time_id_cache[rev] < commit_time_id]

            if not pred_commits:
                return None

            pred_report_commit_hash = max(pred_commits, key=lambda x: x[0])[1]
            return report_files.get(pred_report_commit_hash[:10], None)

        def get_successor_report_file(c_hash: str) -> tp.Optional[Path]:
            commit_time_id = commit_map.short_time_id(c_hash)
            succ_commits = [(short_time_id_cache[rev], rev)
                            for rev in sampled_revs
                            if short_time_id_cache[rev] > commit_time_id]

            if not succ_commits:
                return None

            succ_report_commit_hash = min(succ_commits, key=lambda x: x[0])[1]
            return report_files.get(succ_report_commit_hash[:10], None)

        report_files: tp.Dict[str, Path] = {
            MetaReport.get_commit_hash_from_result_file(report.name): report
            for report in get_processed_revisions_files(
                project_name,
                BlameReport,
                get_case_study_file_name_filter(case_study)
                if case_study else lambda x: False,
            )
        }

        if case_study:
            sampled_revs = case_study.revisions
        else:
            sampled_revs = get_processed_revisions(project_name, BlameReport)
        short_time_id_cache: tp.Dict[str, int] = {
            rev: commit_map.short_time_id(rev) for rev in sampled_revs
        }

        failed_report_files: tp.Dict[str, Path] = {
            MetaReport.get_commit_hash_from_result_file(report.name): report
            for report in get_failed_revisions_files(
                project_name,
                BlameReport,
                get_case_study_file_name_filter(case_study)
                if case_study else lambda x: False,
            )
        }

        report_pairs: tp.List[tp.Tuple[Path, Path]] = [
            (report, pred)
            for report, pred in
            [(report_file, get_predecessor_report_file(c_hash))
             for c_hash, report_file in report_files.items()]
            if pred is not None
        ]

        failed_report_pairs: tp.List[tp.Tuple[Path, Path]] = [
            (report, pred)
            for report, pred in chain.from_iterable([[(
                report_file, get_predecessor_report_file(c_hash)
            ), (get_successor_report_file(c_hash),
                report_file)] for c_hash, report_file in failed_report_files.
                                                     items()])
            if report is not None and pred is not None
        ]

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_pairs, failed_report_pairs,
            create_dataframe_layout, create_data_frame_for_report,
            BlameDiffMetricsDatabase._id_from_paths,
            BlameDiffMetricsDatabase._timestamp_from_paths,
            BlameDiffMetricsDatabase._compare_timestamps
        )

        return data_frame

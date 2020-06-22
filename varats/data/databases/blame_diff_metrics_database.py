"""Module for diff based commit-data metrics."""
import typing as tp
from datetime import datetime
from functools import reduce

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
from varats.utils.git_util import calc_code_churn_range, ChurnConfig
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

        def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
            # Look-up commit and infos about the HEAD commit of the report
            repo = get_local_project_git(project_name)
            commit = repo.get(report.head_commit)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)
            commit_time_id = commit_map.short_time_id(report.head_commit)

            pred_commits = [(commit_map.short_time_id(rev), rev) for rev in (
                case_study.revisions if case_study else
                get_processed_revisions(project_name, BlameReport)
            ) if commit_map.short_time_id(rev) < commit_time_id]

            def empty_data_frame() -> pd.DataFrame:
                return pd.DataFrame({
                    'revision': report.head_commit,
                    'churn': 0,
                    'num_interactions': 0,
                    'num_interacting_commits': 0,
                    'num_interacting_authors': 0,
                    "ci_degree_mean": 0.0,
                    "author_mean": 0.0,
                    "avg_time_mean": 0.0,
                    "ci_degree_max": 0.0,
                    "author_max": 0.0,
                    "avg_time_max": 0.0,
                    'year': commit_date.year,
                },
                                    index=[0])

            if not pred_commits:
                return empty_data_frame()

            pred_report_commit_hash = max(pred_commits, key=lambda x: x[0])[1]

            def is_not_predecessor_revision(revision_file: str) -> bool:
                return not pred_report_commit_hash.startswith(
                    MetaReport.get_commit_hash_from_result_file(revision_file)
                )

            report_files = get_processed_revisions_files(
                project_name, BlameReport, is_not_predecessor_revision
            )

            if not report_files:
                return empty_data_frame()

            diff_between_head_pred = BlameReportDiff(
                report, load_blame_report(report_files[0])
            )

            # Calculate the total churn between pred and base commit
            code_churn = calc_code_churn_range(
                repo, ChurnConfig.create_c_style_languages_config(),
                pred_report_commit_hash, commit
            )
            total_churn = reduce(
                lambda x, y: x + y, [
                    churn_rev[1] + churn_rev[2]
                    for churn_rev in code_churn.values()
                ]
            )

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

            return pd.DataFrame({
                'revision':
                    report.head_commit,
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
                    combine_max(generate_degree_tuples(diff_between_head_pred)),
                "author_max":
                    combine_max(
                        generate_avg_time_distribution_tuples(
                            diff_between_head_pred, project_name, 1
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
                                index=[0])

        report_files = get_processed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study)
        )

        failed_report_files = get_failed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study)
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, create_dataframe_layout,
            create_data_frame_for_report, load_blame_report, report_files,
            failed_report_files
        )

        return data_frame

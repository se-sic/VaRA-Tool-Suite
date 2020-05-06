"""
Module for diff based commit-data metrics.
"""
import typing as tp
from datetime import datetime
from functools import reduce

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
from varats.data.reports.blame_report import (BlameReport, BlameReportDiff,
                                              generate_in_head_interactions,
                                              generate_out_head_interactions)
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (get_processed_revisions_files,
                                   get_failed_revisions_files)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter
from varats.utils.project_util import get_local_project_git
from varats.utils.git_util import (calc_code_churn_range, ChurnConfig)


class BlameDiffMetricsDatabase(EvaluationDatabase,
                               cache_id="blame_diff_metrics_data",
                               columns=["churn_total", "diff_ci_total",
                                        "year"]):
    """
    Metrics database that contains all different blame-interaction metrics that
    are based on a diff between two `BlameReports`.
    """

    @classmethod
    def _load_dataframe(cls, project_name: str, commit_map: CommitMap,
                        case_study: tp.Optional[CaseStudy],
                        **kwargs: tp.Any) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.churn_total = df_layout.churn_total.astype('int64')
            df_layout.diff_ci_total = df_layout.diff_ci_total.astype('int64')
            df_layout.year = df_layout.year.astype('int64')
            return df_layout

        def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
            # Look-up commit and infos about the HEAD commit of the report
            repo = get_local_project_git(project_name)
            commit = repo.get(report.head_commit)
            commit_date = datetime.utcfromtimestamp(commit.commit_time)
            commit_time_id = commit_map.short_time_id(report.head_commit)

            # TODO: if no case study -> fucked
            # Idea find pred with all avail report types
            pred_commits = [(commit_map.short_time_id(rev), rev)
                            for rev in case_study.revisions
                            if commit_map.short_time_id(rev) < commit_time_id]

            def empty_data_frame() -> pd.DataFrame:
                return pd.DataFrame(
                    {
                        'revision': report.head_commit,
                        'churn_total': 0,
                        'diff_ci_total': 0,
                        'year': commit_date.year,
                    },
                    index=[0])

            if not pred_commits:
                return empty_data_frame()

            pred_report_commit_hash = max(pred_commits, key=lambda x: x[0])[1]

            def is_not_predecessor_revision(revision_file: str) -> bool:
                return not pred_report_commit_hash.startswith(
                    MetaReport.get_commit_hash_from_result_file(revision_file))

            report_files = get_processed_revisions_files(
                project_name, BlameReport, is_not_predecessor_revision)

            if not report_files:
                return empty_data_frame()

            diff_between_head_pred = BlameReportDiff(
                report, load_blame_report(report_files[0]))

            # Calculate the total number of commit interactions between the pred
            # and base BlameReport
            ci_total_inters = [
                # we use abs here because we want to capute the total change
                abs(interaction.amount)
                for func_entry in diff_between_head_pred.function_entries
                for interaction in func_entry.interactions
            ]
            ci_total = reduce(lambda x, y: x + y, ci_total_inters, 0)

            # Calculate the total churn between pred and base commit
            code_churn = calc_code_churn_range(
                repo, ChurnConfig.create_c_style_languages_config(),
                pred_report_commit_hash, commit)
            total_churn = reduce(lambda x, y: x + y, [
                churn_rev[1] + churn_rev[2]
                for churn_rev in code_churn.values()
            ])

            return pd.DataFrame(
                {
                    'revision': report.head_commit,
                    'churn_total': total_churn,
                    'diff_ci_total': ci_total,
                    'year': commit_date.year,
                },
                index=[0])

        report_files = get_processed_revisions_files(
            project_name,
            BlameReport,
            # TODO: @boehm is passing here only_newest report_files ok?
            get_case_study_file_name_filter(case_study),
            False)

        failed_report_files = get_failed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study))

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(cls.CACHE_ID, project_name,
                                               create_dataframe_layout,
                                               create_data_frame_for_report,
                                               load_blame_report, report_files,
                                               failed_report_files)

        return data_frame

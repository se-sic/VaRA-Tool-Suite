"""Module for the base CommitInteractionDatabase class."""
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
from varats.data.reports.commit_report import CommitMap, CommitReport
from varats.data.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.jupyterhelper.file import load_commit_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter


class CommitInteractionDatabase(
    EvaluationDatabase,
    cache_id="commit_interaction_data",
    columns=[
        "CFInteractions", "DFInteractions", "HEAD CF Interactions",
        "HEAD DF Interactions"
    ]
):
    """Provides access to commit interaction data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.CFInteractions = df_layout.CFInteractions.astype('int64')
            df_layout.DFInteractions = df_layout.DFInteractions.astype('int64')
            df_layout['HEAD CF Interactions'] = df_layout['HEAD CF Interactions'
                                                         ].astype('int64')
            df_layout['HEAD DF Interactions'] = df_layout['HEAD DF Interactions'
                                                         ].astype('int64')
            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_commit_report(report_path)
            cf_head_interactions_raw = report.number_of_head_cf_interactions()
            df_head_interactions_raw = report.number_of_head_df_interactions()

            return pd.DataFrame({
                'revision':
                    report.head_commit,
                'time_id':
                    commit_map.short_time_id(report.head_commit),
                'CFInteractions':
                    report.number_of_cf_interactions(),
                'DFInteractions':
                    report.number_of_df_interactions(),
                'HEAD CF Interactions':
                    cf_head_interactions_raw[0] + cf_head_interactions_raw[1],
                'HEAD DF Interactions':
                    df_head_interactions_raw[0] + df_head_interactions_raw[1]
            },
                                index=[0]), report.head_commit, str(
                                    report_path.stat().st_mtime_ns
                                )

        report_files = get_processed_revisions_files(
            project_name, CommitReport,
            get_case_study_file_name_filter(case_study)
        )

        failed_report_files = get_failed_revisions_files(
            project_name, CommitReport,
            get_case_study_file_name_filter(case_study)
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report,
            lambda path: MetaReport.get_commit_hash_from_result_file(path.name),
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

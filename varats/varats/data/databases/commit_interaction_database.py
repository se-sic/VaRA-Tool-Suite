"""Module for the base CommitInteractionDatabase class."""
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.commit_report import CommitReport
from varats.jupyterhelper.file import load_commit_report
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilename
from varats.revision.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)


class CommitInteractionDatabase(
    EvaluationDatabase,
    cache_id="commit_interaction_data",
    column_types={
        "CFInteractions": 'int64',
        "DFInteractions": 'int64',
        "HEAD CF Interactions": 'int64',
        "HEAD DF Interactions": 'int64'
    }
):
    """Provides access to commit interaction data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_commit_report(report_path)
            cf_head_interactions_raw = report.number_of_head_cf_interactions()
            df_head_interactions_raw = report.number_of_head_df_interactions()

            return pd.DataFrame({
                'revision':
                    report.head_commit.hash,
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
                                index=[0]), report.head_commit.hash, str(
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
            lambda path: ReportFilename(path).commit_hash.hash,
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

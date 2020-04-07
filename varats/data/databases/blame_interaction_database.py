import typing as tp

import pandas as pd

from varats.data.cache_helper import build_cached_report_table, GraphCacheType
from varats.data.databases.database import Database
from varats.data.reports.blame_report import (BlameReport,
                                              generate_in_head_interactions,
                                              generate_out_head_interactions)
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (get_processed_revisions_files,
                                   get_failed_revisions_files)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter


class BlameInteractionDatabase(Database):
    """
    Provides access to blame interaction data.
    """

    COLUMNS = Database.COLUMNS + [
        "IN_HEAD_Interactions", "OUT_HEAD_Interactions", "HEAD_Interactions"
    ]

    @classmethod
    def _load_dataframe(cls, project_name: str, commit_map: CommitMap,
                        case_study: tp.Optional[CaseStudy]) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=[col for col in cls.COLUMNS])
            df_layout.IN_HEAD_Interactions = \
                df_layout.IN_HEAD_Interactions.astype('int64')
            df_layout.OUT_HEAD_Interactions = \
                df_layout.OUT_HEAD_Interactions.astype('int64')
            df_layout.HEAD_Interactions = \
                df_layout.HEAD_Interactions.astype('int64')
            return df_layout

        def create_data_frame_for_report(report: BlameReport) -> pd.DataFrame:
            in_head_interactions = len(generate_in_head_interactions(report))
            out_head_interactions = len(generate_out_head_interactions(report))

            return pd.DataFrame(
                {
                    'revision':
                        report.head_commit,
                    'time_id':
                        commit_map.short_time_id(report.head_commit),
                    'IN_HEAD_Interactions':
                        in_head_interactions,
                    'OUT_HEAD_Interactions':
                        out_head_interactions,
                    'HEAD_Interactions':
                        in_head_interactions + out_head_interactions
                },
                index=[0])

        report_files = get_processed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study))

        failed_report_files = get_failed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study))

        data_frame = build_cached_report_table(
            GraphCacheType.BlameInteractionData, project_name,
            create_dataframe_layout, create_data_frame_for_report,
            load_blame_report, report_files, failed_report_files)

        return data_frame

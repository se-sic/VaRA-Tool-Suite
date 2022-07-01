"""Module for the base FileStatusDatabase class."""
import typing as tp

import pandas as pd

from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.empty_report import EmptyReport
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_revisions_status_for_case_study
from varats.report.report import FileStatusExtension
from varats.utils.git_util import ShortCommitHash


class FileStatusDatabase(
    EvaluationDatabase,
    cache_id="file_status_data",
    column_types={"file_status": 'str'}
):
    """
    Provides access to file status data.

    This data is not cached, as most of it would be computed for the cache-
    integrity check anyways.
    """

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        result_file_type = kwargs.get("result_file_type", EmptyReport)
        tag_blocked = tp.cast(bool, kwargs.get("tag_blocked", True))

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_revision(
            revision: ShortCommitHash, status: FileStatusExtension
        ) -> pd.DataFrame:
            return pd.DataFrame({
                'revision': revision.hash,
                'time_id': commit_map.short_time_id(revision),
                'file_status': status.get_status_extension()
            },
                                index=[0])

        data_frame = create_dataframe_layout()
        data_frames = []

        if case_study:
            processed_revisions = get_revisions_status_for_case_study(
                case_study, result_file_type, tag_blocked=tag_blocked
            )
            for rev, stat in processed_revisions:
                data_frames.append(create_data_frame_for_revision(rev, stat))

        return pd.concat([data_frame] + data_frames,
                         ignore_index=True,
                         sort=False)

    @classmethod
    def get_data_for_project(
        cls, project_name: str, columns: tp.List[str], commit_map: CommitMap,
        *case_studies: CaseStudy, **kwargs: tp.Any
    ) -> pd.DataFrame:
        """
        Retrieve data for a given project and case study.

        Args:
            project_name: the project to retrieve data for
            columns: the columns the resulting dataframe should have; all column
                     names must occur in the ``COLUMNS`` class variable
            commit_map: the commit map to use
            case_studies: the case study to retrieve data for
            kwargs:
                - result_file_type: the report type to compute the status for
                - tag_blocked: whether to include information about blocked
                               revisions

        Return:
            a pandas dataframe with the given columns and the
        """
        return super().get_data_for_project(
            project_name, columns, commit_map, *case_studies, **kwargs
        )

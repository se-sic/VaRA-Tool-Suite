"""
Module for the base Database class
"""
import abc
import typing as tp

import pandas as pd

from varats.data.reports.commit_report import CommitMap
from varats.paper.case_study import CaseStudy

AvailableColumns = tp.TypeVar("AvailableColumns")


class Database(abc.ABC):

    COLUMNS = ["revision", "time_id"]

    @classmethod
    @abc.abstractmethod
    def load_dataframe(cls, project_name: str, commit_map: CommitMap,
                       case_study: tp.Optional[CaseStudy]) -> pd.DataFrame:
        """

        """

    @classmethod
    def get_data_for_project(
            cls,
            project_name: str,
            columns: tp.List[str],
            commit_map: CommitMap,
            case_study: tp.Optional[CaseStudy] = None) -> pd.DataFrame:

        data: pd.DataFrame = cls.load_dataframe(project_name, commit_map,
                                                case_study)
        assert [*data] == cls.COLUMNS
        assert all(column in cls.COLUMNS for column in columns)

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """
            Filter out all commits that are not in the case study if one was
            selected.
            """
            if case_study is None or data_frame.empty:
                return data_frame
            return data_frame[data_frame.apply(
                lambda x: case_study.has_revision(x["revision"]), axis=1)]

        data = cs_filter(data)
        data = data[columns]

        return data

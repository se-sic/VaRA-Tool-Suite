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
    """
    Base class for accessing report data.

    Subclasses have to provide the following:
        - a list of available columns in the variable ``COLUMNS``
        - an identifier for cache files ``CACHE_ID``
        - a function :func:`_load_dataframe` that loads and transparently caches
          report data
    """

    CACHE_ID = None
    COLUMNS = ["revision", "time_id"]

    @classmethod
    @abc.abstractmethod
    def _load_dataframe(cls, project_name: str, commit_map: CommitMap,
                        case_study: tp.Optional[CaseStudy]) -> pd.DataFrame:
        """
        Load and transparently cache the dataframe for this database class.

        NOTE: this function is not intended for external use.
              Use :func:`get_data_for_project` instead.

        Args:
            project_name: the project to load data for
            commit_map: the commit map to use
            case_study: the case_study to load data for

        Return:
            a pandas dataframe with all the cached data
        """

    @classmethod
    def get_data_for_project(
            cls,
            project_name: str,
            columns: tp.List[str],
            commit_map: CommitMap,
            case_study: tp.Optional[CaseStudy] = None) -> pd.DataFrame:
        """
        Retrieve data for a given project and case study.

        Args:
            project_name: the project to retrieve data for
            columns: the columns the resulting dataframe should have; all column
                     names must occur in the ``COLUMNS`` class variable
            commit_map: the commit map to use
            case_study: the case study to retrieve data for

        Return:
            a pandas dataframe with the given columns and the
        """

        data: pd.DataFrame = cls._load_dataframe(project_name, commit_map,
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

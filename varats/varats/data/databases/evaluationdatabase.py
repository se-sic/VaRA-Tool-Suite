"""Module for the base Database class."""
import abc
import typing as tp

import pandas as pd
from pygtrie import CharTrie

from varats.data.cache_helper import get_data_file_path
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.utils.git_util import ShortCommitHash

AvailableColumns = tp.TypeVar("AvailableColumns")


class EvaluationDatabase(abc.ABC):
    """
    Base class for accessing report data.

    Subclasses have to provide the following:
        - a list of available columns in the variable ``COLUMNS``; this list
          must start with ``Database.COLUMNS``!
        - an identifier for cache files ``CACHE_ID``
        - a function :func:`_load_dataframe` that loads and transparently caches
          report data
    """

    CACHE_ID: str
    COLUMN_TYPES = {"revision": 'str', "time_id": 'int32'}
    COLUMNS: tp.List[str]

    @classmethod
    def __init_subclass__(
        cls, *args: tp.Any, cache_id: str, column_types: tp.Dict[str, str],
        **kwargs: tp.Any
    ) -> None:
        super().__init_subclass__(*args, **kwargs)
        cls.CACHE_ID = cache_id
        cls.COLUMN_TYPES = {**cls.COLUMN_TYPES, **column_types}
        cls.COLUMNS = list(cls.COLUMN_TYPES.keys())

    @classmethod
    @abc.abstractmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:
        """
        Load and transparently cache the dataframe for this database class.

        NOTE: this function is not intended for external use.
              Use :func:`get_data_for_project` instead.

        Args:
            project_name: the project to load data for
            commit_map: the commit map to use
            case_study: the case_study to load data for
            kwargs: additional arguments used to load data

        Return:
            a pandas dataframe with all the cached data
        """

    @classmethod
    def __get_data_for_case_study(
        cls, project_name: str, columns: tp.List[str], commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        data: pd.DataFrame = cls._load_dataframe(
            project_name, commit_map, case_study, **kwargs
        )

        if not [*data] == cls.COLUMNS:
            raise AssertionError(
                "Loaded dataframe does not match expected layout."
                "Consider removing the cache file "
                f"{get_data_file_path(cls.CACHE_ID, project_name)}."
            )

        if not all(column in cls.COLUMNS for column in columns):
            raise ValueError(
                f"All values in 'columns' must be in {cls.__name__}.COLUMNS"
            )

        def cs_filter(data_frame: pd.DataFrame) -> pd.DataFrame:
            """Filter out all commits that are not in the case study if one was
            selected."""
            if case_study is None or data_frame.empty:
                return data_frame
            # use a trie for fast prefix lookup
            revisions = CharTrie()
            for revision in case_study.revisions:
                revisions[revision.hash] = True
            return data_frame[data_frame["revision"].
                              apply(lambda x: revisions.has_node(x.hash) != 0)]

        # Convert all revisions to ShortCommitHash(es)
        data['revision'] = data['revision'].apply(ShortCommitHash)
        data = cs_filter(data)
        return data[columns]

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
            case_studies: the case studies to retrieve data for
            kwargs: additional arguments that are passed to
                    :func:`_load_dataframe()`

        Return:
            a pandas dataframe with the given columns and the
        """
        if cls.__name__ == "Database":
            raise AssertionError(
                "You must not call this function on the "
                "'Database' base class."
            )

        if not case_studies:
            return cls.__get_data_for_case_study(
                project_name, columns, commit_map, None, **kwargs
            )

        data_frames: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            data_frames.append(
                cls.__get_data_for_case_study(
                    project_name, columns, commit_map, case_study, **kwargs
                )
            )
        return pd.concat(data_frames)

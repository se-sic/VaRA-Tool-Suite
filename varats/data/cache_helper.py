"""
Utility functions and class to allow easier caching of pandas dataframe and
other data.
"""

import typing as tp
from enum import Enum
from pathlib import Path

import pandas as pd

from varats.settings import CFG


class GraphCacheType(Enum):
    """
    Cached dataframes for graphs.
    """
    CommitInteractionData = "interaction_table"


def __get_data_file_path(data_id: tp.Union[GraphCacheType, str],
                         project_name: str) -> Path:
    """

    Test:
    >>> str(__get_data_file_path("foo", "tmux"))
    'data_cache/foo-tmux.csv'

    >>> isinstance(__get_data_file_path("foo.csv", "tmux"), Path)
    True

    >>> str(__get_data_file_path(GraphCacheType.CommitInteractionData, "tmux"))
    'data_cache/interaction_table-tmux.csv'
    """
    return Path(str(
        CFG["plots"]["data_cache"])) / "{plot_name}-{project_name}.csv".format(
            plot_name=data_id.value
            if isinstance(data_id, GraphCacheType) else data_id,
            project_name=project_name)


def load_cached_df_or_none(data_id: tp.Union[GraphCacheType, str],
                           project_name: str) -> tp.Optional[pd.DataFrame]:
    """
    Load cached dataframe from disk, otherwise return None.

    Args:
        data_id: File name or GraphCacheType
    """

    file_path = __get_data_file_path(data_id, project_name)
    if not file_path.exists():
        return None

    return pd.read_csv(str(file_path))


def cache_dataframe(data_id: tp.Union[GraphCacheType], project_name: str,
                    dataframe: pd.DataFrame) -> None:
    """
    Cache a dataframe by persisting it to disk.

    Args:
        data_id: File name or GraphCacheType
        df: pandas dataframe to store
    """
    file_path = __get_data_file_path(data_id, project_name)
    dataframe.to_csv(str(file_path))

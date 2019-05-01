"""
Utility functions and class to allow easier caching of pandas dataframe and
other data.
"""

from enum import Enum
from pathlib import Path

import pandas as pd

from varats.settings import CFG


class GraphCacheType(Enum):
    """
    Cached dataframes for graphs.
    """
    CommitInteractionData = "interaction_table.csv"


def __get_data_file_path(data_id):
    """

    Test:
    >>> str(__get_data_file_path("foo.txt"))
    'data_cache/foo.txt'

    >>> isinstance(__get_data_file_path("foo.txt"), Path)
    True

    >>> str(__get_data_file_path(GraphCacheType.CommitInteractionData))
    'data_cache/interaction_table.csv'
    """
    return Path(str(CFG["plots"]["data_cache"])) / (
        data_id.value if isinstance(data_id, GraphCacheType) else data_id)


def load_cached_df_or_none(data_id):
    """
    Load cached dataframe from disk, otherwise return None.

    Args:
        data_id: File name or GraphCacheType
    """

    file_path = __get_data_file_path(data_id)
    if not file_path.exists():
        return None

    return pd.read_csv(str(file_path))


def cache_dataframe(data_id, dataframe: pd.DataFrame):
    """
    Cache a dataframe by persisting it to disk.

    Args:
        data_id: File name or GraphCacheType
        df: pandas dataframe to store
    """
    file_path = __get_data_file_path(data_id)
    dataframe.to_csv(str(file_path))

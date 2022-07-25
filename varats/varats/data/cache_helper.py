"""Utility functions and class to allow easier caching of pandas dataframes and
other data."""
import logging
import typing as tp
from pathlib import Path

import networkx as nx
import pandas as pd

from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)

CACHE_ID_COL = 'cache_revision'
CACHE_TIMESTAMP_COL = 'cache_timestamp'


def get_data_file_path(data_id: str, project_name: str) -> Path:
    """
    Compose the identifier and project into a file path that points to the
    corresponding cache file in the cache directory.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
    """
    return Path(
        str(vara_cfg()["data_cache"])
    ) / f"{data_id}-{project_name}.csv.gz"


def load_cached_df_or_none(
    data_id: str, project_name: str, data_types: tp.Dict[str, str]
) -> tp.Optional[pd.DataFrame]:
    """
    Load cached dataframe from disk, otherwise return None.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
        data_types: dict of columns and types to pass to the dataframe loading
    """

    file_path = get_data_file_path(data_id, project_name)
    if not file_path.exists():
        # fall back to uncompressed file if present for seamless migration
        # to cache file compression
        if Path(str(file_path)[:-3]).exists():
            file_path = Path(str(file_path)[:-3])
        else:
            return None

    return pd.read_csv(
        str(file_path), index_col=0, compression='infer', dtype=data_types
    )


def cache_dataframe(
    data_id: str, project_name: str, dataframe: pd.DataFrame
) -> None:
    """
    Cache a dataframe by persisting it to disk.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
        dataframe: pandas dataframe to store
    """
    file_path = get_data_file_path(data_id, project_name)
    dataframe.to_csv(str(file_path), compression='infer')


InDataType = tp.TypeVar("InDataType")


def __create_cache_entry(
    create_df_from_report: tp.Callable[[InDataType], tp.Tuple[pd.DataFrame, str,
                                                              str]],
    data: InDataType
) -> pd.DataFrame:
    new_df, entry_id, entry_timestamp = create_df_from_report(data)
    new_df[CACHE_ID_COL] = entry_id
    new_df[CACHE_TIMESTAMP_COL] = entry_timestamp
    return new_df


def build_cached_report_table(
    data_id: str, project_name: str, data_to_load: tp.List[InDataType],
    data_to_drop: tp.List[InDataType],
    create_empty_df: tp.Callable[[], pd.DataFrame],
    create_cache_entry_data: tp.Callable[[InDataType], tp.Tuple[pd.DataFrame,
                                                                str, str]],
    get_entry_id: tp.Callable[[InDataType], str],
    get_entry_timestamp: tp.Callable[[InDataType], str],
    is_newer_timestamp: tp.Callable[[str, str], bool]
) -> pd.DataFrame:
    """
    Build up an automatically cache dataframe.

    Args:
        data_id: graph cache identifier
        project_name: name of the project to work with
        data_to_load: list of data items to be loaded
        data_to_drop: list of data items to be discarded
        create_empty_df: creates an empty layout of the dataframe
        create_cache_entry_data: creates a dataframe from a data item
        get_entry_id: returns a unique identifier for one data item
        get_entry_timestamp: returns a string with information that can be used
                             to determine which of two data items is newer
        is_newer_timestamp: checks whether one data item is newer than another
                            based on their timestamps
    """

    # mypy needs this
    empty_df = create_empty_df()
    df_types = empty_df.dtypes.to_dict()
    optional_cached_df = load_cached_df_or_none(data_id, project_name, df_types)
    if optional_cached_df is None:
        cached_df = empty_df
        cached_df[CACHE_ID_COL] = ""
        cached_df[CACHE_TIMESTAMP_COL] = ""
    else:
        cached_df = optional_cached_df

    def is_missing_file(report_file: InDataType) -> bool:
        return not (cached_df[CACHE_ID_COL] == get_entry_id(report_file)).any()

    def is_newer_file(report_file: InDataType) -> bool:
        cached_entry = cached_df[cached_df[CACHE_ID_COL] ==
                                 get_entry_id(report_file)][CACHE_TIMESTAMP_COL]

        if len(cached_entry) > 0:
            return is_newer_timestamp(
                get_entry_timestamp(report_file), cached_entry.iloc[0]
            )
        # We found no existing entry, so it will never be considered for
        # updating and does not need to be deleted.
        return False

    missing_entries = [
        entry for entry in data_to_load if is_missing_file(entry)
    ]

    updated_entries = [entry for entry in data_to_load if is_newer_file(entry)]

    failed_entries = [
        get_entry_id(entry) for entry in data_to_drop if is_newer_file(entry)
    ]

    new_data_frames = []
    for num, data_entry in enumerate(missing_entries):
        LOG.info(
            f"Creating missing entry ({(num + 1)}/"
            f"{len(missing_entries)}): {data_entry}"
        )
        new_data_frames.append(
            __create_cache_entry(create_cache_entry_data, data_entry)
        )

    new_df = pd.concat([cached_df] + new_data_frames,
                       ignore_index=True,
                       sort=False)

    new_df.set_index(CACHE_ID_COL, inplace=True)
    for num, data_entry in enumerate(updated_entries):
        LOG.info(
            f"Updating outdated entry "
            f"({(num + 1)}/{len(updated_entries)}): {data_entry}"
        )
        updated_entry = __create_cache_entry(
            create_cache_entry_data, data_entry
        )
        updated_entry.set_index(CACHE_ID_COL, inplace=True)
        new_df.update(updated_entry)
    new_df.reset_index(inplace=True)

    if len(failed_entries) > 0:
        LOG.info(f"Dropping {len(failed_entries)} entries")
        new_df.drop(
            new_df[new_df[CACHE_ID_COL].isin(failed_entries)].index,
            inplace=True
        )

    cache_dataframe(data_id, project_name, new_df)

    return tp.cast(
        pd.DataFrame, new_df.loc[:, [
            col for col in new_df.columns
            if col not in [CACHE_ID_COL, CACHE_TIMESTAMP_COL]
        ]]
    )


GraphTy = tp.TypeVar("GraphTy", bound=nx.Graph)


def build_cached_graph(
    graph_id: str, create_graph: tp.Callable[[], GraphTy]
) -> GraphTy:
    """
    Create an automatically cached networkx graph.

    Args:
        graph_id: graph cache identifier
        create_graph: function that creates the graph

    Returns:
        the cached or created graph
    """
    path = Path(str(vara_cfg()["data_cache"])) / f"graph-{graph_id}.gz"

    if path.exists():
        return tp.cast(GraphTy, nx.read_gpickle(path))

    graph = create_graph()
    nx.write_gpickle(graph, path)
    return graph

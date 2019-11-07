"""
Utility functions and class to allow easier caching of pandas dataframe and
other data.
"""

import typing as tp
from enum import Enum
from pathlib import Path

import pandas as pd

from varats.settings import CFG
from varats.data.report import BaseReport, MetaReport

CACHE_REVISION_COL = 'cache_revision'
# TODO (se-passau/VaRA#518): rename to plot


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


def build_cached_report_table(
        graph_cache_type: GraphCacheType, project_name: str,
        create_empty_df: tp.Callable[[], pd.DataFrame],
        create_df_from_report: tp.Callable[[tp.Any], pd.DataFrame],
        create_report: tp.Callable[[Path], BaseReport],
        report_files: tp.List[Path]) -> pd.DataFrame:
    """
    Build up an automatically cache dataframe

    Args:
        graph_cache_type: graph cache descriptor
        create_empty_df: create a empty layout of the dataframe
        create_df_from_report: create a dataframe from a report
        create_report: callback to load a report
        report_files: list of files to be loaded
    """

    cached_df = load_cached_df_or_none(graph_cache_type, project_name)
    if cached_df is None:
        cached_df = create_empty_df()
        cached_df[CACHE_REVISION_COL] = ""

    def report_in_data_frame(report_file: Path, df_col: pd.Series) -> bool:
        commit_hash = MetaReport.get_commit_hash_from_result_file(
            report_file.name)
        return tp.cast(bool, (commit_hash == df_col).any())

    missing_report_files = [
        report_file for report_file in report_files
        if not report_in_data_frame(report_file, cached_df[CACHE_REVISION_COL])
    ]

    new_data_frames = []
    total_missing_reports = len(missing_report_files)
    for num, file_path in enumerate(missing_report_files):
        print(
            "Loading missing file ({num}/{total}): ".format(
                num=(num + 1), total=total_missing_reports), file_path)
        try:
            new_df = create_df_from_report(create_report(file_path))
            new_df['cache_revision'] = \
                MetaReport.get_commit_hash_from_result_file(file_path.name)
            new_data_frames.append(new_df)

        except KeyError:
            print("KeyError: ", file_path)
        except StopIteration:
            print("YAML file was incomplete: ", file_path)

    new_df = pd.concat([cached_df] + new_data_frames,
                       ignore_index=True,
                       sort=False)

    cache_dataframe(graph_cache_type, project_name, new_df)

    return new_df.loc[:, new_df.columns != CACHE_REVISION_COL]

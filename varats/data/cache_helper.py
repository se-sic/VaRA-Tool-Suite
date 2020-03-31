"""
Utility functions and class to allow easier caching of pandas dataframes and
other data.
"""
import logging
import typing as tp
from enum import Enum
from pathlib import Path

import pandas as pd

from varats.settings import CFG
from varats.data.report import BaseReport, MetaReport

LOG = logging.getLogger(__name__)

CACHE_REVISION_COL = 'cache_revision'
CACHE_TIMESTAMP_COL = 'cache_timestamp'
# TODO (se-passau/VaRA#518): rename to plot


class GraphCacheType(Enum):
    """
    Identifiers for cached plot dataframes. These identifiers allow a plot to
    refer to a possibly cached dataframe.  Identifiers can be used in multiple
    plots that use the same or a similar dataframe layout, e.g., are based on
    similar data.
    """
    CommitInteractionData = "interaction_table"
    BlameInteractionDegreeData = "b_interaction_degree_table"
    BlameInteractionData = "b_interaction_data"


def __get_data_file_path(data_id: tp.Union[GraphCacheType, str],
                         project_name: str) -> Path:
    """
    Compose the identifier and project into a file path that points to the
    corresponding cache file in the cache directory.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project

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
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
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
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
        dataframe: pandas dataframe to store
    """
    file_path = __get_data_file_path(data_id, project_name)
    dataframe.to_csv(str(file_path))


def __create_cache_entry(create_df_from_report: tp.Callable[[tp.Any],
                                                            pd.DataFrame],
                         create_report: tp.Callable[[Path], BaseReport],
                         file_path: Path) -> pd.DataFrame:
    try:
        new_df = create_df_from_report(create_report(file_path))
        new_df[CACHE_REVISION_COL] = \
            MetaReport.get_commit_hash_from_result_file(file_path.name)
        new_df[CACHE_TIMESTAMP_COL] = file_path.stat().st_mtime
        return new_df
    except KeyError:
        LOG.error(f"KeyError: {file_path}")
    except StopIteration:
        LOG.error(f"YAML file was incomplete: {file_path}")


def build_cached_report_table(graph_cache_type: GraphCacheType,
                              project_name: str,
                              create_empty_df: tp.Callable[[], pd.DataFrame],
                              create_df_from_report: tp.Callable[[tp.Any],
                                                                 pd.DataFrame],
                              create_report: tp.Callable[[Path], BaseReport],
                              report_files: tp.List[Path]) -> pd.DataFrame:
    """
    Build up an automatically cache dataframe

    Args:
        graph_cache_type: graph cache identifier
        project_name: name of the project to work with
        create_empty_df: creates an empty layout of the dataframe
        create_df_from_report: creates a dataframe from a report
        create_report: callback to load a report
        report_files: list of files to be loaded
    """

    # mypy needs this
    optional_cached_df = load_cached_df_or_none(graph_cache_type, project_name)
    if optional_cached_df is None:
        cached_df = create_empty_df()
        cached_df[CACHE_REVISION_COL] = ""
        cached_df[CACHE_TIMESTAMP_COL] = 0
    else:
        cached_df = optional_cached_df

    def is_missing_file(report_file: Path) -> bool:
        commit_hash = MetaReport.get_commit_hash_from_result_file(
            report_file.name)
        return not tp.cast(bool,
                           (commit_hash == cached_df[CACHE_REVISION_COL]).any())

    def is_newer_file(report_file: Path) -> bool:
        commit_hash = MetaReport.get_commit_hash_from_result_file(
            report_file.name)
        return tp.cast(bool,
                       (report_file.stat().st_mtime >
                        cached_df[cached_df[CACHE_REVISION_COL] ==
                                  commit_hash][CACHE_TIMESTAMP_COL]).any())

    missing_report_files = [
        report_file for report_file in report_files
        if is_missing_file(report_file)
    ]

    updated_report_files = [
        report_file for report_file in report_files
        if is_newer_file(report_file)
    ]

    new_data_frames = []
    total_missing_reports = len(missing_report_files)
    for num, file_path in enumerate(missing_report_files):
        LOG.info(f"Loading missing file ({(num + 1)}/{total_missing_reports}): "
                 f"{file_path}")
        new_data_frames.append(
            __create_cache_entry(create_df_from_report, create_report,
                                 file_path))

    new_df = pd.concat([cached_df] + new_data_frames,
                       ignore_index=True,
                       sort=False)

    new_df.set_index(CACHE_REVISION_COL, inplace=True)
    total_updated_reports = len(updated_report_files)
    for num, file_path in enumerate(updated_report_files):
        LOG.info(f"Updating outdated file "
                 f"({(num + 1)}/{total_updated_reports}): {file_path}")
        updated_entry = __create_cache_entry(create_df_from_report,
                                             create_report, file_path)
        updated_entry.set_index(CACHE_REVISION_COL)
        new_df.update(updated_entry)

    new_df.reset_index(inplace=True)
    cache_dataframe(graph_cache_type, project_name, new_df)

    return new_df.loc[:, new_df.columns != CACHE_REVISION_COL]

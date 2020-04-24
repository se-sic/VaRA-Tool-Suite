"""
Utility functions and class to allow easier caching of pandas dataframes and
other data.
"""
import logging
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.report import BaseReport, MetaReport
from varats.settings import CFG

LOG = logging.getLogger(__name__)

CACHE_REVISION_COL = 'cache_revision'
CACHE_TIMESTAMP_COL = 'cache_timestamp'


def get_data_file_path(data_id: str, project_name: str) -> Path:
    """
    Compose the identifier and project into a file path that points to the
    corresponding cache file in the cache directory.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project

    Test:
    >>> str(get_data_file_path("foo", "tmux"))
    'data_cache/foo-tmux.csv'

    >>> isinstance(get_data_file_path("foo.csv", "tmux"), Path)
    True
    """
    return Path(str(
        CFG["plots"]["data_cache"])) / f"{data_id}-{project_name}.csv.gz"


def load_cached_df_or_none(data_id: str,
                           project_name: str) -> tp.Optional[pd.DataFrame]:
    """
    Load cached dataframe from disk, otherwise return None.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
    """

    file_path = get_data_file_path(data_id, project_name)
    if not file_path.exists():
        # fall back to uncompressed file if present for seamless migration
        # to cache file compression
        if Path(str(file_path)[:-3]).exists():
            file_path = Path(str(file_path)[:-3])
        else:
            return None

    return pd.read_csv(str(file_path), index_col=0, compression='infer')


def cache_dataframe(data_id: str, project_name: str,
                    dataframe: pd.DataFrame) -> None:
    """
    Cache a dataframe by persisting it to disk.

    Args:
        data_id: identifier or identifier_name of the dataframe
        project_name: name of the project
        dataframe: pandas dataframe to store
    """
    file_path = get_data_file_path(data_id, project_name)
    dataframe.to_csv(str(file_path), compression='infer')


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


def build_cached_report_table(
        data_id: str, project_name: str,
        create_empty_df: tp.Callable[[], pd.DataFrame],
        create_df_from_report: tp.Callable[[tp.Any], pd.DataFrame],
        create_report: tp.Callable[[Path],
                                   BaseReport], report_files: tp.List[Path],
        failed_report_files: tp.List[Path]) -> pd.DataFrame:
    """
    Build up an automatically cache dataframe

    Args:
        data_id: graph cache identifier
        project_name: name of the project to work with
        create_empty_df: creates an empty layout of the dataframe
        create_df_from_report: creates a dataframe from a report
        create_report: callback to load a report
        report_files: list of files to be loaded
        failed_report_files: list of files to be discarded
    """

    # mypy needs this
    optional_cached_df = load_cached_df_or_none(data_id, project_name)
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

    failed_revisions = [
        MetaReport.get_commit_hash_from_result_file(failed_file.name)
        for failed_file in failed_report_files
        if is_newer_file(failed_file)
    ]

    new_data_frames = []
    for num, file_path in enumerate(missing_report_files):
        LOG.info(f"Loading missing file ({(num + 1)}/"
                 f"{len(missing_report_files)}): {file_path}")
        new_data_frames.append(
            __create_cache_entry(create_df_from_report, create_report,
                                 file_path))

    new_df = pd.concat([cached_df] + new_data_frames,
                       ignore_index=True,
                       sort=False)

    new_df.set_index(CACHE_REVISION_COL, inplace=True)
    for num, file_path in enumerate(updated_report_files):
        LOG.info(f"Updating outdated file "
                 f"({(num + 1)}/{len(updated_report_files)}): {file_path}")
        updated_entry = __create_cache_entry(create_df_from_report,
                                             create_report, file_path)
        updated_entry.set_index(CACHE_REVISION_COL)
        new_df.update(updated_entry)
    new_df.reset_index(inplace=True)

    if len(failed_revisions) > 0:
        LOG.info(f"Dropping {len(failed_revisions)} newly failing file(s)")
        new_df.drop(
            new_df[new_df[CACHE_REVISION_COL].isin(failed_revisions)].index,
            inplace=True)

    cache_dataframe(data_id, project_name, new_df)

    return new_df.loc[:, [
        col for col in new_df.columns
        if col not in [CACHE_REVISION_COL, CACHE_TIMESTAMP_COL]
    ]]

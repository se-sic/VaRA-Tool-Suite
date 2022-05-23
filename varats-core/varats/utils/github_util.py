"""Utility module for working with the pygithub API."""
import codecs
import logging
import pickle  # nosec
import re
import typing as tp
from pathlib import Path

import pandas as pd
from benchbuild.project import Project
from benchbuild.source import primary
from github import Github
from github.GithubObject import GithubObject

from varats.utils.settings import vara_cfg

if tp.TYPE_CHECKING:
    # pylint: disable=unused-import,ungrouped-imports
    from github.PaginatedList import PaginatedList

LOG = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(r"https://github\.com/(.*)/(.*)\.git")


def get_github_instance() -> Github:
    """
    Creates a Github instance using a github access token if configured.

    Returns:
        a Github instance
    """
    access_token = str(vara_cfg()["provider"]["github_access_token"])
    if access_token:
        return Github(access_token)
    return Github()


__PYGITHUB_CACHE_FILE_NAME = "pygithub.csv.gz"
__PYGITHUB_KEY_COLUMN = "key"
__PYGITHUB_LIST_LENGTH_COLUMN = "length"
__PYGITHUB_OBJECT_COLUMN = "object"

PyGithubObj = tp.TypeVar("PyGithubObj", bound=GithubObject)


def _dump_pygithub_object(obj: GithubObject) -> str:
    """
    Pickle a GithubObject.

    Args:
        obj: the object to pickle

    Returns:
        the pickled object
    """
    return codecs.encode(
        pickle.dumps((obj.__class__, obj.raw_data, obj.raw_headers)), "base64"
    ).decode()


def _load_pygithub_object(obj: str) -> GithubObject:
    """
    Unpickle a GithubObject.

    Args:
        obj: the object to unpickle

    Returns:
        the unpickled object
    """
    return tp.cast(
        GithubObject,
        get_github_instance().create_from_raw_data(
            *pickle.loads(codecs.decode(obj.encode(), "base64"))  # nosec
        )
    )


def _load_cache_file() -> pd.DataFrame:
    cache_file = Path(
        str(vara_cfg()["data_cache"])
    ) / __PYGITHUB_CACHE_FILE_NAME
    if cache_file.exists():
        cache_df = pd.read_csv(
            str(cache_file), index_col=0, compression='infer'
        )
        return cache_df
    return pd.DataFrame(
        columns=[
            __PYGITHUB_KEY_COLUMN, __PYGITHUB_OBJECT_COLUMN,
            __PYGITHUB_LIST_LENGTH_COLUMN
        ]
    )


def _store_cache_file(cache_df: pd.DataFrame) -> None:
    cache_file = Path(
        str(vara_cfg()["data_cache"])
    ) / __PYGITHUB_CACHE_FILE_NAME
    cache_df.to_csv(str(cache_file), compression='infer')


def _cache_pygithub_object(key: str, obj: GithubObject) -> None:
    """
    Cache a GithubObject.

    Args:
        key: the unique identifier for the object to store
        obj: the object to store
    """
    cache_df = _load_cache_file()
    cache_df = cache_df.append({
        __PYGITHUB_KEY_COLUMN: key,
        __PYGITHUB_OBJECT_COLUMN: _dump_pygithub_object(obj)
    },
                               ignore_index=True)
    _store_cache_file(cache_df)


def _get_cached_pygithub_object(key: str) -> tp.Optional[GithubObject]:
    """
    Load a GithubObject from the cache.

    Args:
        key: the unique identifier of the object to load

    Returns:
        the cached object if available, else ``None``
    """
    cache_df = _load_cache_file()
    selected_rows = cache_df[cache_df[__PYGITHUB_KEY_COLUMN] == key]
    if selected_rows.empty:
        return None
    return _load_pygithub_object(selected_rows[__PYGITHUB_OBJECT_COLUMN].item())


def _cache_pygithub_object_list(key: str, objs: tp.List[PyGithubObj]) -> None:
    """
    Cache a list of GithubObjects.

    Args:
        key: the unique identifier for the list to store
    """
    cache_df = _load_cache_file()
    cache_df = cache_df.append({
        __PYGITHUB_KEY_COLUMN: key,
        __PYGITHUB_LIST_LENGTH_COLUMN: len(objs)
    },
                               ignore_index=True)
    for idx, obj in enumerate(objs):
        cache_df = cache_df.append({
            __PYGITHUB_KEY_COLUMN: f"{key}_{idx}",
            __PYGITHUB_OBJECT_COLUMN: _dump_pygithub_object(obj)
        },
                                   ignore_index=True)
        _store_cache_file(cache_df)


def _get_cached_pygithub_object_list(
    key: str
) -> tp.Optional[tp.List[GithubObject]]:
    """
    Load a list of GithubObjects from the cache.

    Args:
        key: the unique identifier of the list to load

    Returns:
        the cached list if available, else ``None``
    """
    cache_df = _load_cache_file()
    list_header = cache_df[cache_df[__PYGITHUB_KEY_COLUMN] == key]
    if list_header.empty:
        return None
    list_length: int = int(list_header[__PYGITHUB_LIST_LENGTH_COLUMN].item())
    selected_rows = pd.DataFrame()
    for idx in range(list_length):
        selected_rows = selected_rows.append(
            cache_df[cache_df[__PYGITHUB_KEY_COLUMN] == f"{key}_{idx}"],
            ignore_index=True
        )
    if len(selected_rows) != list_length:
        raise AssertionError("List length is not equal to list header.")
    return [
        _load_pygithub_object(obj)
        for obj in selected_rows[__PYGITHUB_OBJECT_COLUMN].tolist()
    ]


def get_cached_github_object(
    cached_object_key: str, load_function: tp.Callable[[Github], PyGithubObj]
) -> PyGithubObj:
    """
    Transparently caches a GithubObj loaded by the given function.

    Args:
        cached_object_key: unique name to identify the GithubObj
        load_function: function that loads a GithubObj

    Returns:
         the fetched or cached GithubObj
    """
    cached_object = _get_cached_pygithub_object(cached_object_key)
    if cached_object:
        return tp.cast(PyGithubObj, cached_object)

    obj_to_cache = load_function(get_github_instance())
    _cache_pygithub_object(cached_object_key, obj_to_cache)
    return obj_to_cache


def get_cached_github_object_list(
    cached_object_key: str,
    load_function: 'tp.Callable[[Github], PaginatedList[PyGithubObj]]'
) -> tp.List[PyGithubObj]:
    """
    Transparently caches a PaginatedList of GithubObjs loaded by the given
    function.

    Args:
        cached_object_key: unique name to identify the GithubObj list
        load_function: function that loads a PaginatedList of PygithubObjs

    Returns:
         the fetched or cached list of GithubObjs
    """
    cached_list = _get_cached_pygithub_object_list(cached_object_key)
    if cached_list:
        return [tp.cast(PyGithubObj, obj) for obj in cached_list]

    obj_list_to_cache = list(load_function(get_github_instance()))
    # if list shall be cached manually:
    # _cache_pygithub_object_list(cached_object_key, obj_list_to_cache)
    return obj_list_to_cache


def get_github_repo_name_for_project(
    project: tp.Type[Project]
) -> tp.Optional[str]:
    """
    Finds the github repo name corresponding to a given github project.

    Args:
        project: class of said project

    Returns:
        the github repo name for the project or ``None`` if the given project
        is not a github project
    """
    match = GITHUB_URL_PATTERN.match(primary(*project.SOURCE).remote)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None

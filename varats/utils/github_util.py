"""Utility module for working with the pygithub API."""
import logging
import typing as tp
from pathlib import Path

from github import Github, GithubException
from github.GithubObject import GithubObject
from github.PaginatedList import PaginatedList

from varats.settings import _CFG as CFG

LOG = logging.getLogger(__name__)


def get_github_instance() -> Github:
    access_token = str(CFG["provider"]["github_access_token"])
    if access_token:
        return Github(access_token)
    return Github()


PyGithubObj = tp.TypeVar("PyGithubObj", bound=GithubObject)


# TODO: extend to handle paginated lists
def get_cached_github_object(
    cache_file_name: str, load_function: tp.Callable[[Github], PyGithubObj]
) -> tp.Optional[PyGithubObj, tp.List[PyGithubObj]]:
    """
    Wrapper function for accessing specified data from a github project. Creates
    a Github instance for given project and passes it to given function.

    Args:
        cache_file_name: Path to the cache file for the project to extract the data from.
        load_function: Function taking a Github object as argument and returning a PygithubObj.

    Returns:
         The output specified by load_function or None in case of a GithubException occurring.
    """
    github = get_github_instance()
    cache_file = Path(str(CFG["data_cache"])) / f"pygithub_{cache_file_name}"

    try:
        if cache_file.exists():
            return tp.cast(PyGithubObj, github.load(cache_file))

        obj_to_cache = load_function(github)
        if isinstance(obj_to_cache, PaginatedList):
            obj_to_cache = list(obj_to_cache)
        github.dump(obj_to_cache, cache_file, protocol=4)
        return obj_to_cache
    except GithubException as exception:
        LOG.error("Failed to load Github Object from Cache", exception)
    return None

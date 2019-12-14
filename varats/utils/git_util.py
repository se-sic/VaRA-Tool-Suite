"""
Utility module for handling git repos.
"""

import typing as tp
from varats.utils.project_util import get_local_project_git

import pygit2


def create_commit_lookup_helper(project_name: str
                               ) -> tp.Callable[[str], pygit2.Commit]:
    """
    Creates a commit lookup function for a specific repository.
    """

    cache_dict: tp.Dict[str, pygit2.Commit] = {}
    repo = get_local_project_git(project_name)

    def get_commit(c_hash: str) -> pygit2.Commit:
        if c_hash in cache_dict:
            return cache_dict[c_hash]

        commit = repo.get(c_hash)
        if commit is None:
            raise LookupError(
                "Could not find commit {commit} in {project}".format(
                    commit=c_hash, project=project_name))

        cache_dict[c_hash] = commit
        return commit

    return get_commit


def map_commits(func: tp.Callable[[pygit2.Commit], tp.Any],
                c_hash_list: tp.Iterable[str], commit_lookup):
    # Skip 0000 hashes that we added to mark uncommited files
    return [
        func(commit_lookup(c_hash))
        for c_hash in c_hash_list
        if c_hash != "0000000000000000000000000000000000000000"
    ]

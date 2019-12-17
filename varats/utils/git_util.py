"""
Utility module for handling git repos.
"""

import typing as tp
import re

import pygit2
from plumbum.cmd import git
from plumbum import local

from varats.utils.project_util import get_local_project_git


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


MC_RET = tp.TypeVar("MC_RET")


def map_commits(func: tp.Callable[[pygit2.Commit], MC_RET],
                c_hash_list: tp.Iterable[str],
                commit_lookup: tp.Callable[[str], pygit2.Commit]
               ) -> tp.Sequence[MC_RET]:
    # Skip 0000 hashes that we added to mark uncommitted files
    return [
        func(commit_lookup(c_hash))
        for c_hash in c_hash_list
        if c_hash != "0000000000000000000000000000000000000000"
    ]


GIT_LOG_MATCHER = re.compile(r"\'(?P<hash>.*)\'\n?" +
                             r"( (?P<files>\d*) files? changed)?" +
                             r"(, (?P<insertions>\d*) insertions?\(\+\))?" +
                             r"(, (?P<deletions>\d*) deletions?\(-\))?")


def __calc_code_churn_range_impl(repo_path: str,
                                 start_range: tp.Optional[str] = None,
                                 end_range: tp.Optional[str] = None
                                ) -> tp.Dict[str, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range [start..end]
    If no range is supplied, the churn values of all commits are calculated.

    git log --pretty=format:'%H' --date=short --shortstat
    """

    churn_values: tp.Dict[str, tp.Tuple[int, int, int]] = {}

    if start_range is None and end_range is None:
        revision_range = None
    elif start_range is None:
        revision_range = "..{}".format(end_range)
    elif end_range is None:
        revision_range = "{}~..".format(start_range)
    else:
        revision_range = "{}~..{}".format(start_range, end_range)

    with local.cwd(repo_path):
        base_params = [
            "log", "--pretty=format:'%H'", "--date=short", "--shortstat", "-l0"
        ]
        if revision_range:
            stdout = git(base_params, revision_range)
        else:
            stdout = git(base_params)
        print(stdout)
        for match in GIT_LOG_MATCHER.finditer(stdout):
            commit_hash = match.group('hash')
            files_changed_m = match.group('files')
            files_changed = int(
                files_changed_m) if files_changed_m is not None else 0
            insertions_m = match.group('insertions')
            insertions = int(insertions_m) if insertions_m is not None else 0
            deletions_m = match.group('deletions')
            deletions = int(deletions_m) if deletions_m is not None else 0
            churn_values[commit_hash] = (files_changed, insertions, deletions)

    # Sadly, pygit2 currently gives us wrong/different diffs for renames, therefore,
    # we have to fall back to calling git directly.
    #
    #for commit in repo.walk(repo.head.target, pygit2.GIT_SORT_TIME):
    #    churn = calc_code_churn(repo, commit)
    #    pred = commit.parents[0]
    #    diff = repo.diff(pred, commit)
    #    churn_values[commit.id] = (diff.stats.files_changed, diff.stats.insertions,
    #                               diff.stats.deletions)
    return churn_values


def calc_code_churn_range(
        repo: tp.Union[pygit2.Repository, str],
        start_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None,
        end_range: tp.Optional[tp.Union[pygit2.Commit, str]] = None
) -> tp.Dict[str, tp.Tuple[int, int, int]]:
    """
    Calculates all churn values for the commits in the specified range [start..end]
    If no range is supplied, the churn values of all commits are calculated.
    """
    return __calc_code_churn_range_impl(
        repo.path if isinstance(repo, pygit2.Repository) else repo,
        start_range.id
        if isinstance(start_range, pygit2.Commit) else start_range,
        end_range.id if isinstance(end_range, pygit2.Commit) else end_range)


def calc_commit_code_churn(repo: pygit2.Repository,
                           commit: pygit2.Commit) -> tp.Tuple[int, int, int]:
    """
    Calculates churn of a specific commit.
    """
    return calc_code_churn_range(repo, commit, commit)[str(commit.id)]


def calc_repo_code_churn(repo: pygit2.Repository
                        ) -> tp.Dict[str, tp.Tuple[int, int, int]]:
    """
    Calculates code churn for a repository.

    """
    return calc_code_churn_range(repo)


def __print_calc_repo_code_churn(repo: pygit2.Repository):
    """
    Prints calc repo code churn data like git log would do.

    git log --pretty=format:'%H' --date=short --shortstat
    """
    churn_map = calc_repo_code_churn(repo)
    for commit in repo.walk(repo.head.target, pygit2.GIT_SORT_TIME):
        commit_hash = str(commit.id)
        print(commit_hash)

        churn = churn_map[commit_hash]
        if churn[0] == 1:
            changed_files = " 1 file changed"
        else:
            changed_files = " {} files changed".format(churn[0])

        if churn[1] == 0:
            insertions = ""
        elif churn[1] == 1:
            insertions = ", 1 insertion(+)"
        else:
            insertions = ", {} insertions(+)".format(churn[1])

        if churn[2] == 0:
            deletions = ""
        elif churn[2] == 1:
            deletions = ", 1 deletion(-)"
        else:
            deletions = ", {} deletions(-)".format(churn[2])

        if churn[0] > 0 and churn[1] == 0 and churn[2] == 0:
            insertions = ", 0 insertions(+)"
            deletions = ", 0 deletions(-)"

        if churn[0] > 0:
            print(changed_files + insertions + deletions)
            print()

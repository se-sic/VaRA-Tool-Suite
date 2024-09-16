"""This module contains wrapper for basic git commands."""
import typing as tp
from pathlib import Path

from benchbuild.utils.cmd import git

from varats.utils.git_util import (
    get_current_branch,
    CommitHash,
    RepositoryHandle,
    FullCommitHash,
)


def add_remote(repo: RepositoryHandle, remote: str, url: str) -> None:
    """Adds new remote to the repository."""
    repo("remote", "add", remote, url)


def show_status(repo: RepositoryHandle) -> None:
    """Show git status."""
    repo("status")


def get_branches(
    repo: RepositoryHandle,
    extra_args: tp.Optional[tp.List[str]] = None
) -> str:
    """Show git branches."""
    args = ["branch"]
    if extra_args:
        args += extra_args

    return tp.cast(str, repo(*args))


def get_tags(
    repo: RepositoryHandle,
    extra_args: tp.Optional[tp.List[str]] = None
) -> tp.List[str]:
    """Get the list of available git tags."""

    args = ["tag"]
    if extra_args:
        args += extra_args

    git_tag_string: str = repo(*args)
    git_tag_list: tp.List[str] = []

    if git_tag_string:
        git_tag_list = git_tag_string.split("\n")
        git_tag_list.remove('')
        return git_tag_list

    return git_tag_list


def init_all_submodules(repo: RepositoryHandle) -> None:
    """Inits all submodules."""
    repo("submodule", "init")


def update_all_submodules(
    repo: RepositoryHandle, recursive: bool = True, init: bool = False
) -> None:
    """Updates all submodules."""
    git_params = ["submodule", "update"]
    if recursive:
        git_params.append("--recursive")
    if init:
        git_params.append("--init")
    repo(*git_params)


def get_submodules(repo: RepositoryHandle) -> tp.List[RepositoryHandle]:
    submodule_paths = repo("submodule", "--quiet", "foreach", "echo $path")
    return [
        RepositoryHandle(repo.worktree_path / path)
        for path in submodule_paths.splitlines()
    ]


def get_submodule_updates(repo: RepositoryHandle,
                          submodule_path: str) -> tp.List[FullCommitHash]:
    """
    Get all commits that update the given submodule.

    Args:
        repo: repository handle
        submodule_name: the submodule to find upgrades for
    Returns:
        a list of submodule upgrading commits
    """
    submodule_log = repo("log", "--pretty=%H", "--", submodule_path)
    return [FullCommitHash(c) for c in submodule_log.strip().split()]


def fetch_remote(
    repo: RepositoryHandle,
    remote: tp.Optional[str] = None,
    extra_args: tp.Optional[tp.List[str]] = None
) -> None:
    """Fetches the new changes from the remote."""
    args = ["fetch"]
    if extra_args:
        args += extra_args
    if remote:
        args.append(remote)
    repo(*args)


def pull_current_branch(repo: RepositoryHandle) -> None:
    """Pull in changes in a certain branch."""
    repo("pull")


def push_current_branch(
    repo: RepositoryHandle,
    upstream: tp.Optional[str] = None,
    branch_name: tp.Optional[str] = None
) -> None:
    """Push in changes in a certain branch."""
    cmd_args = ["push"]

    if upstream is not None:
        cmd_args.append("--set-upstream")
        cmd_args.append(upstream)
        if branch_name is not None:
            cmd_args.append(branch_name)
        else:
            cmd_args.append(get_current_branch(repo))

    repo(*cmd_args)


def fetch_repository(repo: RepositoryHandle) -> None:
    """Pull in changes in a certain branch."""
    repo("fetch")


def add(repo_folder: Path, *git_add_args: str) -> None:
    """Runs `git add` with the given arguments."""
    git("-C", repo_folder.absolute(), "add", *git_add_args)


def commit(
    repo_folder: Path,
    message: tp.Optional[str] = None,
    allow_empty: bool = False
) -> None:
    """Commits the repository."""
    args = ["--allow-empty-message"]
    if message:
        args = ["-m", message]
    if allow_empty:
        args += ["--allow-empty"]

    git("-C", repo_folder.absolute(), "commit", *args)


def checkout_branch_or_commit(
    repo: RepositoryHandle, target: tp.Union[str, CommitHash]
) -> None:
    """Checks out a branch or commit in the repository."""
    repo("checkout", str(target))


def checkout_new_branch(
    repo: RepositoryHandle,
    branch: str,
    remote_branch: tp.Optional[str] = None
) -> None:
    """Checks out a new branch in the repository."""
    args = ["checkout", "-b", branch]
    if remote_branch is not None:
        args.append(remote_branch)
    repo(*args)


def download_repo(
    dl_folder: Path,
    url: str,
    repo_name: tp.Optional[str] = None,
    remote_name: tp.Optional[str] = None,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Download a repo into the specified folder."""
    if not dl_folder.exists():
        raise Exception(f"Could not find download folder  {dl_folder}")

    args = ["clone", "--progress", url]
    if remote_name is not None:
        args.append("--origin")
        args.append(remote_name)

    if repo_name is not None:
        args.append(repo_name)

    output = git("-C", dl_folder, args)
    for line in output.split("\n"):
        post_out(line)


def apply_patch(repo: RepositoryHandle, patch_file: Path) -> None:
    """Applies a given patch file to the specified git repository."""
    repo("apply", str(patch_file))


def revert_patch(repo: RepositoryHandle, patch_file: Path) -> None:
    """Reverts a given patch file on the specified git repository."""
    repo("apply", "-R", str(patch_file))

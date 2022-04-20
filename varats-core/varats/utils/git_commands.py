"""This module contains wrapper for basic git commands."""
import typing as tp
from pathlib import Path

from benchbuild.utils.cmd import git

from varats.utils.git_util import get_current_branch, CommitHash


def add_remote(repo_folder: Path, remote: str, url: str) -> None:
    """Adds new remote to the repository."""
    git(["-C", repo_folder.absolute(), "remote", "add", remote, url])


def show_status(repo_folder: Path) -> None:
    """Show git status."""
    git["-C", repo_folder.absolute(), "status"].run_fg()


def get_branches(
    repo_folder: Path, extra_args: tp.Optional[tp.List[str]] = None
) -> str:
    """Show git branches."""
    args = ["branch"]
    if extra_args:
        args += extra_args

    return tp.cast(str, git("-C", repo_folder.absolute(), args))


def get_tags(repo_folder: Path,
             extra_args: tp.Optional[tp.List[str]] = None) -> tp.List[str]:
    """Get the list of available git tags."""

    args = ["tag"]
    if extra_args:
        args += extra_args

    git_tag_string: str = git("-C", repo_folder.absolute(), args)
    git_tag_list: tp.List[str] = []

    if git_tag_string:
        git_tag_list = git_tag_string.split("\n")
        git_tag_list.remove('')
        return git_tag_list

    return git_tag_list


def init_all_submodules(folder: Path) -> None:
    """Inits all submodules."""
    git("-C", folder.absolute(), "submodule", "init")


def update_all_submodules(folder: Path, recursive: bool = True) -> None:
    """Updates all submodules."""
    git_params = ["submodule", "update"]
    if recursive:
        git_params.append("--recursive")
    git("-C", folder, git_params)


def fetch_remote(
    remote: tp.Optional[str] = None,
    repo_folder: tp.Optional[Path] = None,
    extra_args: tp.Optional[tp.List[str]] = None
) -> None:
    """Fetches the new changes from the remote."""
    args = ["fetch"]
    if extra_args:
        args += extra_args
    if remote:
        args.append(remote)
    git("-C", repo_folder, args)


def pull_current_branch(repo_folder: Path) -> None:
    """Pull in changes in a certain branch."""
    git("-C", repo_folder.absolute(), "pull")


def push_current_branch(
    repo_folder: tp.Optional[Path] = None,
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
            cmd_args.append(get_current_branch(repo_folder))

    if repo_folder is None or repo_folder == Path(""):
        git(cmd_args)
    else:
        git("-C", repo_folder.absolute(), cmd_args)


def fetch_repository(repo_folder: tp.Optional[Path] = None) -> None:
    """Pull in changes in a certain branch."""
    git("-C", repo_folder, "fetch")


def checkout_branch_or_commit(
    repo_folder: Path, target: tp.Union[str, CommitHash]
) -> None:
    """Checks out a branch or commit in the repository."""
    git("-C", repo_folder.absolute(), "checkout", str(target))


def checkout_new_branch(
    repo_folder: Path,
    branch: str,
    remote_branch: tp.Optional[str] = None
) -> None:
    """Checks out a new branch in the repository."""
    args = ["checkout", "-b", branch]
    if remote_branch is not None:
        args.append(remote_branch)
    git("-C", repo_folder.absolute(), args)


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

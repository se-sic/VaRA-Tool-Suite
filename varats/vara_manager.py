#!/usr/bin/env python3
"""
This module handels the status of VaRA.
Setting up the tooling, keeping it up to date,
and providing necessary information.
"""

import os

from plumbum import local, FG
from plumbum.cmd import git, mkdir, ln


def download_repo(dl_folder, url: str, repo_name=None):
    """
    Download a repo into the specified folder.
    """
    if not os.path.isdir(dl_folder):
        # TODO: error
        return

    with local.cwd(dl_folder):
        if repo_name is not None:
            git["clone", url, repo_name] & FG
        else:
            git["clone", url] & FG


def add_remote(repo_folder, remote, url):
    """
    Adds new remote to the repository.
    """
    with local.cwd(repo_folder):
        git["remote", "add", remote, url] & FG
        git["fetch", remote] & FG


def checkout_branch(repo_folder, branch):
    """
    Checks out a branch in the repository.
    """
    with local.cwd(repo_folder):
        git["checkout", branch] & FG


def checkout_new_branch(repo_folder, branch, remote_branch):
    """
    Checks out a new branch in the repository.
    """
    with local.cwd(repo_folder):
        git["checkout", "-b", branch, remote_branch] & FG


def download_vara(dl_folder):
    """
    Downloads VaRA an all other necessary repos from github.
    """
    download_repo(dl_folder, "https://git.llvm.org/git/llvm.git")
    dl_folder += "llvm/"
    add_remote(dl_folder, "upstream", "git@github.com:se-passau/vara-llvm.git")

    download_repo(dl_folder + "tools/", "https://git.llvm.org/git/clang.git")
    add_remote(dl_folder + "tools/clang/", "upstream",
               "git@github.com:se-passau/vara-clang.git")

    download_repo(dl_folder + "tools/", "git@github.com:se-passau/VaRA.git")

    download_repo(dl_folder + "tools/clang/tools/",
                  "https://git.llvm.org/git/clang-tools-extra.git", "extra")

    download_repo(dl_folder + "tools/", "https://git.llvm.org/git/lld.git")

    download_repo(dl_folder + "projects/",
                  "https://git.llvm.org/git/compiler-rt.git")

    mkdir[dl_folder + "build/"] & FG
    with local.cwd(dl_folder + "build/"):
        ln["-s", dl_folder + "tools/VaRA/utils/vara/builds/", "build_cfg"] & FG


def checkout_vara_version(llvm_folder, version, dev):
    """
    Checks out all related repositories to match the VaRA version number.

    ../llvm/ 60 dev
    """
    version = str(version)
    version_name = ""
    version_name += version
    if dev:
        version_name += "-dev"
    print(version_name)
    checkout_new_branch(llvm_folder, "vara-" + version_name,
                        "upstream/vara-" + version_name)
    checkout_new_branch(llvm_folder + "tools/clang/", "vara-" + version_name,
                        "upstream/vara-" + version_name)
    if dev:
        checkout_branch(llvm_folder + "tools/VaRA/", "vara-dev")

    checkout_branch(llvm_folder + "tools/clang/tools/extra/",
                    "release_" + version)
    checkout_branch(llvm_folder + "tools/lld/", "release_" + version)
    checkout_branch(llvm_folder + "projects/compiler-rt/",
                    "release_" + version)


def init_vara_build(build_type):
    """
    Initialize a VaRA build config.
    """
    # TODO: needs enum
    pass


def build_vara(build_type):
    """
    Builds VaRA
    """
    # TODO: needs enum
    pass


if __name__ == "__main__":
    download_vara("/tmp/foo/")
    checkout_vara_version("/tmp/foo/llvm/", 60, True)

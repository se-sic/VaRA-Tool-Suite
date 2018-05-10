#!/usr/bin/env python3
"""
This module handels the status of VaRA.
Setting up the tooling, keeping it up to date,
and providing necessary information.
"""

import os

from enum import Enum

from plumbum import local, FG
from plumbum.cmd import git, mkdir, ln, ninja, grep, cmake


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


class BuildType(Enum):
    """
    This enum containts all VaRA prepared Build configurations.
    """
    DBG = 1
    DEV = 2
    OPT = 3
    PGO = 4


def get_cmake_var(var_name):
    print(grep(var_name, "CMakeCache.txt"))
    # TODO: find way to get cmake var
    raise NotImplementedError


def set_cmake_var(var_name, value):
    cmake("-D" + var_name + "=" + value, ".")


def init_vara_build(path_to_llvm, build_type: BuildType):
    """
    Initialize a VaRA build config.
    """
    full_path = path_to_llvm + "build/"
    if not os.path.exists(full_path):
        os.makedirs(full_path)

    with local.cwd(full_path):
        if build_type == BuildType.DEV:
            local["./build_cfg/build-dev.sh"] & FG


def build_vara(path_to_llvm: str, install_prefix: str, build_type: BuildType):
    """
    Builds a VaRA configuration
    """
    full_path = path_to_llvm + "build/"
    if build_type == BuildType.DEV:
        full_path += "dev/"
    if not os.path.exists(full_path):
        init_vara_build(path_to_llvm, build_type)

    with local.cwd(full_path):
        set_cmake_var("CMAKE_INSTALL_PREFIX", install_prefix)
        ninja["install"] & FG


if __name__ == "__main__":
    download_vara("/tmp/foo/")
    checkout_vara_version("/tmp/foo/llvm/", 60, True)

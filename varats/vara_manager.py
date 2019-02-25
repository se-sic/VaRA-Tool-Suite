#!/usr/bin/env python3
"""
This module handels the status of VaRA.
Setting up the tooling, keeping it up to date,
and providing necessary information.
"""

import os
import re
import subprocess as sp

from enum import Enum
from varats.settings import save_config, CFG

from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject

from plumbum import local, FG
from plumbum.cmd import git, mkdir, ln, ninja, grep, cmake, cut
from plumbum.commands.processes import ProcessExecutionError


def run_with_output(pb_cmd, post_out=lambda x: None):
    """
    Run plumbum command and post output lines to function.
    """
    try:
        with pb_cmd.bgrun(universal_newlines=True,
                          stdout=sp.PIPE, stderr=sp.STDOUT) as p_gc:
            while p_gc.poll() is None:
                for line in p_gc.stdout:
                    post_out(line)
    except ProcessExecutionError:
        post_out("ProcessExecutionError")


def download_repo(dl_folder, url: str, repo_name=None, remote_name=None,
                  post_out=lambda x: None):
    """
    Download a repo into the specified folder.
    """
    if not os.path.isdir(dl_folder):
        # TODO: error
        return

    with local.cwd(dl_folder):
        args = ["clone", "--progress", url]
        if remote_name is not None:
            args.append("--origin")
            args.append(remote_name)

        if repo_name is not None:
            args.append(repo_name)

        git_clone = git[args]
        run_with_output(git_clone, post_out)


class BuildType(Enum):
    """
    This enum contains all VaRA prepared Build configurations.
    """
    DBG = 1
    DEV = 2
    OPT = 3
    PGO = 4


def setup_vara(init, update, build, llvm_folder, install_prefix, own_libgit,
               version, build_type: BuildType, post_out=lambda x: None):
    """
    Sets up VaRA over cli.
    """

    CFG["llvm_source_dir"] = llvm_folder
    CFG["llvm_install_dir"] = install_prefix
    #CFG["version"] = version
    save_config()

    if init:
        if os.path.exists(llvm_folder):
            print("LLVM was already checked out in '%s'.", llvm_folder)
        else:
            download_vara(llvm_folder, post_out=post_out)
            checkout_vara_version(llvm_folder, version,
                                  build_type == BuildType.DEV)
            if own_libgit:
                init_all_submodules(llvm_folder + "/tools/VaRA/")
                update_all_submodules(llvm_folder + "/tools/VaRA/")

    if not os.path.exists(llvm_folder):
        print("LLVM was not initialized. Please initialize LLVM with VaRA, " +
              "for example, with 'vara-buildsetup -i'.")
    else:
        if update:
            if str(CFG["version"]) != str(version):
                fetch_current_branch(llvm_folder)
                fetch_current_branch(llvm_folder + "tools/clang/")
                fetch_current_branch(llvm_folder + "tools/clang/tools/extra/")
                fetch_current_branch(llvm_folder + "tools/VaRA/")
                fetch_current_branch(llvm_folder + "tools/lld/")
                fetch_current_branch(llvm_folder + "projects/compiler-rt/")

                version_name = ""
                version_name += str(version)
                if build_type == BuildType.DEV:
                    version_name += "-dev"
                checkout_branch(llvm_folder, "vara-" + version_name)
                checkout_branch(llvm_folder + "/tools/clang/", "vara-" +
                                version_name)
                if build_type == BuildType.DEV:
                    checkout_branch(llvm_folder + "/tools/VaRA/", "vara-dev")

                checkout_branch(llvm_folder + "/tools/clang/tools/extra/",
                                "release_" + str(version))
                checkout_branch(llvm_folder + "/tools/lld/",
                                "release_" + str(version))
                checkout_branch(llvm_folder + "/projects/compiler-rt/",
                                "release_" + str(version))

                CFG["version"] = int(version)
                save_config()

            pull_current_branch(llvm_folder)
            pull_current_branch(llvm_folder + "tools/clang/")
            pull_current_branch(llvm_folder + "tools/VaRA/")
            if own_libgit:
                update_all_submodules(llvm_folder + "/tools/VaRA/")

        if build:
            build_vara(own_libgit, llvm_folder, install_prefix=install_prefix,
                       build_type=build_type, post_out=post_out)


def add_remote(repo_folder, remote, url):
    """
    Adds new remote to the repository.
    """
    with local.cwd(repo_folder):
        git["remote", "add", remote, url] & FG
        git["fetch", remote] & FG


def fetch_remote(remote, repo_folder=""):
    """
    Fetches the new changes from the remote.
    """
    if repo_folder == '':
        git["fetch", remote] & FG
    else:
        with local.cwd(repo_folder):
            git["fetch", remote] & FG


def init_all_submodules(folder):
    """
    Inits all submodules.
    """
    with local.cwd(folder):
        git["submodule", "init"] & FG


def update_all_submodules(folder):
    """
    Updates all submodules.
    """
    with local.cwd(folder):
        git["submodule", "update"] & FG


def pull_current_branch(repo_folder=""):
    """
    Pull in changes in a certain branch.
    """
    if repo_folder == '':
        git["pull"] & FG
    else:
        with local.cwd(repo_folder):
            git["pull"] & FG


def fetch_current_branch(repo_folder=""):
    """
    Pull in changes in a certain branch.
    """
    if repo_folder == '':
        git["fetch"] & FG
    else:
        with local.cwd(repo_folder):
            git["fetch"] & FG


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


def get_download_steps():
    """
    Returns the amount of steps it takes to download VaRA. This can be used to
    track the progress during the long download phase.
    """
    return 6


def download_vara(llvm_source_folder, progress_func=lambda x: None,
                  post_out=lambda x: None):
    """
    Downloads VaRA an all other necessary repos from github.
    """
    dl_folder, llvm_dir = os.path.split(os.path.normpath(llvm_source_folder))

    progress_func(0)
    download_repo(dl_folder, "https://git.llvm.org/git/llvm.git", llvm_dir,
                  remote_name="upstream", post_out=post_out)
    dl_folder += "/" + llvm_dir + "/"
    add_remote(dl_folder, "origin", "git@github.com:se-passau/vara-llvm.git")

    progress_func(1)
    download_repo(dl_folder + "tools/", "https://git.llvm.org/git/clang.git",
                  remote_name="upstream", post_out=post_out)
    add_remote(dl_folder + "tools/clang/", "origin",
               "git@github.com:se-passau/vara-clang.git")

    progress_func(2)
    download_repo(dl_folder + "tools/", "git@github.com:se-passau/VaRA.git",
                  remote_name="origin", post_out=post_out)

    progress_func(3)
    download_repo(dl_folder + "tools/clang/tools/",
                  "https://git.llvm.org/git/clang-tools-extra.git", "extra",
                  remote_name="upstream", post_out=post_out)

    progress_func(4)
    download_repo(dl_folder + "tools/", "https://git.llvm.org/git/lld.git",
                  remote_name="upstream", post_out=post_out)

    progress_func(5)
    download_repo(dl_folder + "projects/",
                  "https://git.llvm.org/git/compiler-rt.git",
                  remote_name="upstream", post_out=post_out)

    progress_func(6)
    mkdir[dl_folder + "build/"] & FG
    with local.cwd(dl_folder + "build/"):
        ln["-s", dl_folder + "tools/VaRA/utils/vara/builds/", "build_cfg"] & FG


def checkout_vara_version(llvm_folder, version, dev):
    """
    Checks out all related repositories to match the VaRA version number.

    ../llvm/ 60 dev
    """
    llvm_folder = os.path.normpath(llvm_folder)
    version = str(version)
    version_name = ""
    version_name += version
    if dev:
        version_name += "-dev"

    checkout_new_branch(llvm_folder, "vara-" + version_name,
                        "origin/vara-" + version_name)
    checkout_new_branch(llvm_folder + "/tools/clang/", "vara-" + version_name,
                        "origin/vara-" + version_name)
    if dev:
        checkout_branch(llvm_folder + "/tools/VaRA/", "vara-dev")

    checkout_branch(llvm_folder + "/tools/clang/tools/extra/",
                    "release_" + version)
    checkout_branch(llvm_folder + "/tools/lld/", "release_" + version)
    checkout_branch(llvm_folder + "/projects/compiler-rt/",
                    "release_" + version)


def get_cmake_var(var_name):
    """
    Fetch the value of a cmake variable from the current cmake config.
    """
    for line in iter(cmake("-LA", "-N", "CMakeLists.txt").splitlines()):
        if var_name not in line:
            continue
        return line.split("=")[1] == "ON"
    return False


def set_cmake_var(var_name, value, post_out=lambda x: None):
    """
    Sets a cmake variable in the current cmake config.
    """
    run_with_output(cmake["-D" + var_name + "=" + value, "."], post_out)


def init_vara_build(path_to_llvm, build_type: BuildType,
                    post_out=lambda x: None):
    """
    Initialize a VaRA build config.
    """
    full_path = path_to_llvm + "build/"
    if not os.path.exists(full_path):
        os.makedirs(full_path)

    with local.cwd(full_path):
        if build_type == BuildType.DEV:
            cmake = local["./build_cfg/build-dev.sh"]
            run_with_output(cmake, post_out)


def build_vara(own_libgit: bool, path_to_llvm: str, install_prefix: str,
               build_type: BuildType, post_out=lambda x: None):
    """
    Builds a VaRA configuration
    """
    full_path = path_to_llvm + "build/"
    if build_type == BuildType.DEV:
        full_path += "dev/"
    if not os.path.exists(full_path):
        init_vara_build(path_to_llvm, build_type, post_out)

    with local.cwd(full_path):
        verify_build_structure(own_libgit, path_to_llvm, install_prefix,
                               post_out)
        b_ninja = ninja["install"]
        run_with_output(b_ninja, post_out)


def verify_build_structure(own_libgit: bool, path_to_llvm: str,
                           install_prefix: str, post_out=lambda x: None):
    if (not get_cmake_var("VARA_BUILD_LIBGIT") or not os.path.exists(
            path_to_llvm + "/tools/VaRA/external/libgit2/CMakeLists.txt")) and own_libgit:
        init_all_submodules(path_to_llvm + "/tools/VaRA/")
        update_all_submodules(path_to_llvm + "/tools/VaRA/")
    if own_libgit:
        set_cmake_var("VARA_BUILD_LIBGIT", "ON", post_out)
    else:
        set_cmake_var("VARA_BUILD_LIBGIT", "OFF", post_out)
    set_cmake_var("CMAKE_INSTALL_PREFIX", install_prefix, post_out)


###############################################################################
# Git Handling
###############################################################################


class GitState(Enum):
    """
    Represent the direct state of a branch.
    """
    OK = 1
    BEHIND = 2
    ERROR = 3


class GitStatus(object):
    """
    Represents the current update status of a git repository.
    """

    def __init__(self, state, msg: str = ""):
        self.__state = state
        self.__msg = msg

    @property
    def state(self) -> GitState:
        """
        Current state of the git.
        """
        return self.__state

    @property
    def msg(self):
        """
        Additional msg.
        """
        return self.__msg

    def __str__(self):
        if self.state == GitState.OK:
            return "OK"
        elif self.state == GitState.BEHIND:
            return self.msg
        return "Error"


def get_llvm_status(llvm_folder) -> GitStatus:
    """
    Retrieve the git status of llvm.
    """
    with local.cwd(llvm_folder):
        fetch_remote('origin')
        git_status = git['status']
        stdout = git_status('-sb')
        for line in stdout.split('\n'):
            if line.startswith('## vara-' + str(CFG['version']) + '-dev'):
                match = re.match(r".*\[(.*)\]", line)
                if match is not None:
                    return GitStatus(GitState.BEHIND, match.group(1))
                return GitStatus(GitState.OK)

    return GitStatus(GitState.ERROR)


def get_clang_status(llvm_folder) -> GitStatus:
    """
    Retrieve the git status of clang.
    """
    with local.cwd(llvm_folder + 'tools/clang'):
        fetch_remote('origin')
        git_status = git['status']
        stdout = git_status('-sb')
        for line in stdout.split('\n'):
            if line.startswith('## vara-' + str(CFG['version']) + '-dev'):
                match = re.match(r".*\[(.*)\]", line)
                if match is not None:
                    return GitStatus(GitState.BEHIND, match.group(1))
                return GitStatus(GitState.OK)

    return GitStatus(GitState.ERROR)


def get_vara_status(llvm_folder) -> GitStatus:
    """
    Retrieve the git status of VaRA.
    """
    with local.cwd(llvm_folder + 'tools/VaRA'):
        fetch_remote('origin')
        git_status = git['status']
        stdout = git_status('-sb')
        for line in stdout.split('\n'):
            if line.startswith('## vara-dev'):
                match = re.match(r".*\[(.*)\]", line)
                if match is not None:
                    return GitStatus(GitState.BEHIND, match.group(1))
                return GitStatus(GitState.OK)

    return GitStatus(GitState.ERROR)


###############################################################################
# Qt interaction hanlders
###############################################################################

class GitStateSignals(QObject):
    """
    GitStateSignals to send state update to the GUI.
    """
    status_update = pyqtSignal(object, object, object)

class CheckStateSignal(QObject):
    """
    This signal is emited when the state could have changed.
    """
    possible_state_change = pyqtSignal()

class GitStateChecker(QRunnable):
    """
    GitStateChecker to fetch and verify the git status.
    """

    def __init__(self, state_signal, path_to_llvm):
        super(GitStateChecker, self).__init__()
        self.path_to_llvm = path_to_llvm
        self.signals = state_signal

    @pyqtSlot()
    def run(self):
        """
        Retrieve status updates for llvm,clang, and VaRA
        """
        llvm_status = get_llvm_status(self.path_to_llvm)
        clang_status = get_clang_status(self.path_to_llvm)
        vara_status = get_vara_status(self.path_to_llvm)

        self.signals.status_update.emit(llvm_status, clang_status, vara_status)


class PullWorker(QRunnable):
    """
    QtWorker to update repositories.
    """
    def __init__(self, llvm_folder):
        super(PullWorker, self).__init__()
        self.llvm_folder = llvm_folder
        self.check_state = CheckStateSignal()

    @pyqtSlot()
    def run(self):
        """
        Pull changes and update the current branch.
        """
        pull_current_branch(self.llvm_folder)
        pull_current_branch(self.llvm_folder + "tools/clang/")
        pull_current_branch(self.llvm_folder + "tools/VaRA/")
        self.check_state.possible_state_change.emit()


class VaRAStateManager(object):
    """
    """
    def __init__(self, llvm_folder):
        # TODO path propertie needs check
        self.llvm_folder = llvm_folder
        self.state_signal = GitStateSignals()

        self.thread_pool = QThreadPool()

    def change_llvm_source_folder(self, llvm_folder):
        """
        Change the current llvm source folder.
        """
        self.llvm_folder = llvm_folder

    def check_repo_state(self):
        """
        Check the state of the three VaRA repos.
        """
        worker = GitStateChecker(self.state_signal, self.llvm_folder)
        self.thread_pool.start(worker)

    def update_current_branch(self):
        """
        Update the current branches of the VaRA setup.
        """
        worker = PullWorker(self.llvm_folder)
        worker.check_state.possible_state_change.connect(self.check_repo_state)
        self.thread_pool.start(worker)


if __name__ == "__main__":
    download_vara("/tmp/foo/llvm")
    checkout_vara_version("/tmp/foo/llvm/", CFG['version'], True)

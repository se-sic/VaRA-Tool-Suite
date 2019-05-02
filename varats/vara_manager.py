#!/usr/bin/env python3
"""
This module handels the status of VaRA.
Setting up the tooling, keeping it up to date,
and providing necessary information.
"""

import os
import re
import subprocess as sp
import tempfile

from enum import Enum
from threading import RLock
from varats.settings import save_config, CFG

from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject, QThread, QProcess

from plumbum import local
from plumbum.cmd import git, mkdir, ln, grep, cmake
from plumbum.commands.processes import ProcessExecutionError


# TODO: rename to 'run_plumbum_with_output'
def run_with_output(pb_cmd, post_out=lambda x: None):
    """
    Run plumbum command and post output lines to function.
    """
    print("vara_manager: run_with_output() begin")
    try:
        with pb_cmd.bgrun(universal_newlines=True,
                          stdout=sp.PIPE, stderr=sp.STDOUT) as p_gc:
            while p_gc.poll() is None:
                for line in p_gc.stdout:
                    post_out(line)
    except ProcessExecutionError:
        post_out("ProcessExecutionError")
    print("vara_manager: run_with_output() end")

def run_qprocess_with_output(process: QProcess, post_out=lambda x: None):
    output = str(process.readAllStandardOutput().data().decode('utf-8'))
    for line in output.splitlines(True):
        post_out(line)

# TODO (julianbreiteneicher): Return success
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

        proc = QProcess()
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: run_qprocess_with_output(proc, post_out))
        ProcessManager.start_process(proc, "git", args)
        proc.waitForFinished(-1)


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
            build_vara(llvm_folder, install_prefix=install_prefix,
                       build_type=build_type, post_out=post_out)


def add_remote(repo_folder, remote, url):
    """
    Adds new remote to the repository.
    """
    with local.cwd(repo_folder):
        proc = QProcess()
        ProcessManager.start_process(proc, "git", ["remote", "add", remote, url])
        proc.waitForFinished(-1)

        proc = QProcess()
        ProcessManager.start_process(proc, "git", ["fetch", remote])
        proc.waitForFinished(-1)


def fetch_remote(remote, repo_folder=""):
    """
    Fetches the new changes from the remote.
    """
    proc = QProcess()

    if repo_folder == '':
        ProcessManager.start_process(proc, "git", ["fetch", remote])
    else:
        with local.cwd(repo_folder):
            ProcessManager.start_process(proc, "git", ["fetch", remote])
    proc.waitForFinished(-1)


def init_all_submodules(folder):
    """
    Inits all submodules.
    """
    proc = QProcess()
    with local.cwd(folder):
        ProcessManager.start_process(proc, "git", ["submodule", "init"])
    proc.waitForFinished(-1)


def update_all_submodules(folder):
    """
    Updates all submodules.
    """
    proc = QProcess()
    with local.cwd(folder):
        ProcessManager.start_process(proc, "git", ["submodule", "update"])
    proc.waitForFinished(-1)


def pull_current_branch(repo_folder=""):
    """
    Pull in changes in a certain branch.
    """
    proc = QProcess()
    if repo_folder == '':
        ProcessManager.start_process(proc, "git", ["pull"])
    else:
        with local.cwd(repo_folder):
            ProcessManager.start_process(proc, "git", ["pull"])
    proc.waitForFinished(-1)


def fetch_current_branch(repo_folder=""):
    """
    Pull in changes in a certain branch.
    """
    proc = QProcess()
    if repo_folder == '':
        ProcessManager.start_process(proc, "git", ["fetch"])
    else:
        with local.cwd(repo_folder):
            ProcessManager.start_process(proc, "git", ["fetch"])
    proc.waitForFinished(-1)



def checkout_branch(repo_folder, branch):
    """
    Checks out a branch in the repository.
    """
    with local.cwd(repo_folder):
        proc = QProcess()
        ProcessManager.start_process(proc, "git", ["checkout", branch])
        proc.waitForFinished(-1)


def checkout_new_branch(repo_folder, branch, remote_branch):
    """
    Checks out a new branch in the repository.
    """
    with local.cwd(repo_folder):
        proc = QProcess()
        ProcessManager.start_process(proc, "git", ["checkout", "-b", branch, remote_branch])
        proc.waitForFinished(-1)


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
    mkdir(dl_folder + "build/")
    with local.cwd(dl_folder + "build/"):
        ln("-s", dl_folder + "tools/VaRA/utils/vara/builds/", "build_cfg")


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
    proc = QProcess()
    proc.setProcessChannelMode(QProcess.MergedChannels)
    proc.readyReadStandardOutput.connect(lambda: run_qprocess_with_output(proc, post_out))
    ProcessManager.start_process(proc, "cmake", ["-D" + var_name + "=" + value, "."])
    proc.waitForFinished(-1)


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
            proc = QProcess()
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(lambda: run_qprocess_with_output(proc, post_out))
            ProcessManager.start_process(proc, "./build_cfg/build-dev.sh", [])
            proc.waitForFinished(-1)


def verify_build_structure(own_libgit: bool, path_to_llvm: str,
                           post_out=lambda x: None):
    """
    Verify the build strucutre of VaRA:
        - ensure status of submodules
        - update submodules
    """
    if (not get_cmake_var("VARA_BUILD_LIBGIT") or not os.path.exists(
            path_to_llvm + "/tools/VaRA/external/libgit2/CMakeLists.txt")) \
            and own_libgit:
        init_all_submodules(path_to_llvm + "/tools/VaRA/")
        update_all_submodules(path_to_llvm + "/tools/VaRA/")


def build_vara(path_to_llvm: str, install_prefix: str,
               build_type: BuildType, post_out=lambda x: None):
    """
    Builds a VaRA configuration
    """
    own_libgit = bool(CFG["own_libgit2"])
    full_path = path_to_llvm + "build/"
    if build_type == BuildType.DEV:
        full_path += "dev/"
    print("vara_manager: build_vara() - 1")
    if not os.path.exists(full_path):
        init_vara_build(path_to_llvm, build_type, post_out)

    with local.cwd(full_path):
        print("vara_manager: build_vara() - 2")
        verify_build_structure(own_libgit, path_to_llvm, post_out)
        print("vara_manager: build_vara() - 3")
        set_vara_cmake_variables(own_libgit, install_prefix, post_out)
        print("vara_manager: build_vara() - 4")

        proc = QProcess()
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: run_qprocess_with_output(proc, post_out))
        ProcessManager.start_process(proc, "ninja", ["install"])
        print("vara_manager: build_vara() - 5")
        proc.waitForFinished(-1)
        print("vara_manager: build_vara() - 6")


def set_vara_cmake_variables(own_libgit: bool, install_prefix: str,
                             post_out=lambda x: None):
    """
    Set all wanted/needed cmake flags.
    """
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


def get_llvm_project_status(llvm_folder, project_folder="") -> GitStatus:
    """
    Retrieve the git status of a llvm project.
    """
    with local.cwd(llvm_folder + project_folder):
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
        llvm_status = get_llvm_project_status(self.path_to_llvm)
        clang_status = get_llvm_project_status(self.path_to_llvm,
                                               "tools/clang")
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


class ProcessManager:
    __instance = None

    @staticmethod
    def getInstance():
        if ProcessManager.__instance == None:
            ProcessManager()
        return ProcessManager.__instance

    @staticmethod
    def start_process(process: QProcess, program: str, args: [str]):
        ProcessManager.getInstance().__start_process(process, program, args)

    @staticmethod
    def shutdown():
        inst = ProcessManager.getInstance()
        with inst.__mutex:
            inst.__shutdown()
            inst.__terminate_all_processes(block=False)

    @staticmethod
    def terminate_all_processes(block=False):
        ProcessManager.getInstance().__terminate_all_processes(block)

    def __init__(self):
        if ProcessManager.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            ProcessManager.__instance = self

        self.__has_shutdown = False
        self.__processes = []
        self.__mutex = RLock()

    def __process_finished(self):
        print("ProcessManager: __process__finished() begin")
        with self.__mutex:
            self.__processes = [x for x in self.__processes if x.state() != QProcess.NotRunning]
            print("ProcessManager: __process__finished() end")

    def __start_process(self, process: QProcess, program: str, args: [str]):
        print("ProcessManager: __start_process() begin")
        with self.__mutex:
            if self.__has_shutdown:
                print("ProcessManager has already shutdown.")
                return
            process.finished.connect(self.__process_finished)
            self.__processes.append(process)
            process.start(program, args)
            print("ProcessManager: __start_process() end")

    def __shutdown(self):
        print("ProcessManager: __shutdown() begin")
        with self.__mutex:
            self.__has_shutdown = True
            print("ProcessManager: __shutdown() end")

    def __terminate_all_processes(self, block=False):
        print("ProcessManager: __terminate_all_processes() begin")
        with self.__mutex:
            for process in self.__processes:
                process.finished.disconnect(self.__process_finished)
                process.kill()
                #process.terminate()
                if block:
                    print("ProcessManager: Waiting for process to terminate!")
                    process.waitForFinished(-1)
                    print("ProcessManager: Finished waiting!")
            self.__processes.clear()
            print("ProcessManager: __terminate_all_processes() end")

    def __del__(self):
        with self.__mutex:
            self.__shutdown()
            self.__terminate_all_processes(block=False)


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
    with tempfile.TemporaryDirectory() as tmp_dir:
        download_vara(tmp_dir + "/llvm")
        checkout_vara_version(tmp_dir + "/llvm/", CFG['version'], True)

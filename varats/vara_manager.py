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
from pathlib import Path
import shutil

from contextlib import contextmanager
from enum import Enum
from threading import RLock
from varats.utils.exceptions import ProcessTerminatedError

from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject, QThread, QProcess

from plumbum import local, TF
from plumbum.cmd import git, mkdir, ln, ninja, grep, cmake
from plumbum.commands.processes import ProcessExecutionError

from varats.settings import save_config, CFG


class LLVMProject():
    """
    A sub project of LLVM.
    """

    def __init__(self, name: str, URL: str, remote: str, sub_path: str):
        self.__name = name
        self.__url = URL
        self.__remote = remote
        self.__sub_path = Path(sub_path)

    @property
    def name(self):
        """
        Name of the project
        """
        return self.__name

    @property
    def url(self):
        """
        Repository URL
        """
        return self.__url

    @property
    def remote(self):
        """
        Git remote
        """
        return self.__remote

    @property
    def path(self) -> Path:
        """
        Path to the project folder within llvm.
        """
        return self.__sub_path

    def __str__(self):
        return "{name} [{url}:{remote}] {folder}".format(
            name=self.name, url=self.url, remote=self.remote, folder=self.path)


class LLVMProjects(Enum):
    """
    Mapping of all LLVM projects to paths.
    """
    llvm = LLVMProject("llvm", "https://git.llvm.org/git/llvm.git", "upstream",
                       "")
    clang = LLVMProject("clang", "https://git.llvm.org/git/clang.git",
                        "upstream", "tools/clang")
    vara = LLVMProject("VaRA", "git@github.com:se-passau/VaRA.git", "origin",
                       "tools/VaRA")
    clang_extra = LLVMProject(
        "clang_extra", "https://git.llvm.org/git/clang-tools-extra.git",
        "upstream", "tools/clang/tools/extra")
    compiler_rt = LLVMProject("compiler-rt",
                              "https://git.llvm.org/git/compiler-rt.git",
                              "upstream", "projects/compiler-rt")
    lld = LLVMProject("lld", "https://git.llvm.org/git/lld.git", "upstream",
                      "tools/lld")

    def __str__(self):
        return str(self.value)

    @property
    def name(self):
        """
        Name of the project
        """
        return self.value.name

    @property
    def url(self):
        """
        Repository URL
        """
        return self.value.url

    @property
    def remote(self):
        """
        Git remote
        """
        return self.value.remote

    @property
    def path(self):
        """
        Path to the project within llvm.
        """
        return self.value.path

    def is_vara_project(self) -> bool:
        """
        Checks if this a VaRA controled projected.
        """
        return self is LLVMProjects.llvm or self is LLVMProjects.clang or\
            self is LLVMProjects.vara

    def is_extra_project(self) -> bool:
        """
        Checks wether this is an external llvm project.
        """
        return not self.is_vara_project()


class VaRAProjectsIter():
    """
    Iterator over vara projects, meaning projects that are modfified to work with VaRA.
    """

    def __init__(self):
        self.__llvm_project_iter = iter(LLVMProjects)

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            val = next(self.__llvm_project_iter)
            if val.is_vara_project():
                return val


class VaRAExtraProjectsIter():
    """
    Iterator over all additional projects without VaRAs own mofified projects.
    """

    def __init__(self):
        self.__llvm_project_iter = iter(LLVMProjects)

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            val = next(self.__llvm_project_iter)
            if val.is_extra_project():
                return val


# TODO: rename to 'run_plumbum_with_output'
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

def run_process_with_output(process: QProcess, post_out=lambda x: None):
    output = str(process.readAllStandardOutput().data().decode('utf-8'))
    for line in output.splitlines(True):
        post_out(line)

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

        with ProcessManager.create_process("git", args) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(lambda: run_process_with_output(proc, post_out))


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

    if not isinstance(llvm_folder, Path):
        llvm_folder = Path(llvm_folder)

    CFG["llvm_source_dir"] = str(llvm_folder)
    CFG["llvm_install_dir"] = install_prefix
    save_config()

    if init:
        if os.path.exists(llvm_folder):
            print("LLVM was already checked out in '%s'.", llvm_folder)
        else:
            download_vara(llvm_folder, post_out=post_out)
            checkout_vara_version(llvm_folder, version,
                                  build_type == BuildType.DEV)
            if own_libgit:
                init_all_submodules(llvm_folder / LLVMProjects.vara.path)
                update_all_submodules(llvm_folder / LLVMProjects.vara.path)

    if not os.path.exists(llvm_folder):
        print("LLVM was not initialized. Please initialize LLVM with VaRA, " +
              "for example, with 'vara-buildsetup -i'.")
    else:
        if update:
            if str(CFG["version"]) != str(version):
                for project in LLVMProjects:
                    fetch_repository(llvm_folder / project.path)

                version_name = ""
                version_name += str(version)
                if build_type == BuildType.DEV:
                    version_name += "-dev"
                checkout_branch(llvm_folder, "vara-" + version_name)
                checkout_branch(llvm_folder / LLVMProjects.clang.path,
                                "vara-" + version_name)
                if build_type == BuildType.DEV:
                    checkout_branch(llvm_folder / LLVMProjects.vara.path,
                                    "vara-dev")

                for project in VaRAExtraProjectsIter():
                    checkout_branch(llvm_folder / project.path,
                                    "release_" + str(version))

                CFG["version"] = int(version)
                save_config()

            pull_current_branch(llvm_folder)
            pull_current_branch(llvm_folder / LLVMProjects.clang.path)
            pull_current_branch(llvm_folder / LLVMProjects.vara.path)
            if own_libgit:
                update_all_submodules(llvm_folder / LLVMProjects.vara.path)

        if build:
            build_vara(llvm_folder, install_prefix=install_prefix,
                       build_type=build_type, post_out=post_out)


def add_remote(repo_folder, remote, url):
    """
    Adds new remote to the repository.
    """
    with ProcessManager.create_process("git", ["remote", "add", remote, url], workdir=repo_folder):
        pass

    with ProcessManager.create_process("git", ["fetch", remote], workdir=repo_folder):
        pass

def show_status(repo_folder):
    """
    Show git status.
    """
    with local.cwd(repo_folder):
        git["status"].run_fg()


def get_branches(repo_folder, extra_args=None) -> str:
    """
    Show git branches.
    """
    extra_args = [] if extra_args is None else extra_args

    args = ["branch"]
    args += extra_args

    with local.cwd(repo_folder):
        return git(args)


def fetch_remote(remote, repo_folder=None, extra_args=None):
    """
    Fetches the new changes from the remote.
    """
    extra_args = [] if extra_args is None else extra_args

    args = ["fetch"]
    args += extra_args
    args.append(remote)

    with ProcessManager.create_process("git", args, workdir=repo_folder):
        pass


def init_all_submodules(folder):
    """
    Inits all submodules.
    """
    with ProcessManager.create_process("git", ["submodule", "init"], workdir=folder):
        pass


def update_all_submodules(folder):
    """
    Updates all submodules.
    """
    with ProcessManager.create_process("git", ["submodule", "update"], workdir=folder):
        pass


def pull_current_branch(repo_folder=None):
    """
    Pull in changes in a certain branch.
    """
    with ProcessManager.create_process("git", ["pull"], workdir=repo_folder):
        pass


def push_current_branch(repo_folder="", upstream=None, branch_name=None):
    """
    Push in changes in a certain branch.
    """
    cmd_args = ["push"]

    if upstream is not None:
        cmd_args.append("--set-upstream")
        cmd_args.append(upstream)
        if branch_name is not None:
            cmd_args.append(branch_name)
        else:
            cmd_args.append(get_current_branch(repo_folder))

    if repo_folder == '':
        git(cmd_args)
    else:
        with local.cwd(repo_folder):
            git(cmd_args)


def fetch_repository(repo_folder=None):
    """
    Pull in changes in a certain branch.
    """
    with ProcessManager.create_process("git", ["fetch"], workdir=repo_folder):
        pass


def checkout_branch(repo_folder, branch):
    """
    Checks out a branch in the repository.
    """
    with ProcessManager.create_process("git", ["checkout", branch], workdir=repo_folder):
        pass


def checkout_new_branch(repo_folder, branch, remote_branch=None):
    """
    Checks out a new branch in the repository.
    """
    args = ["checkout", "-b", branch]
    if remote_branch is not None:
        args.append(remote_branch)
    with ProcessManager.create_process("git", args, workdir=repo_folder):
        pass


def get_current_branch(repo_folder) -> str:
    """
    Get the current branch of a repository, e.g., HEAD.
    """
    if repo_folder == '':
        return git("rev-parse", "--abbrev-ref", "HEAD").strip()

    with local.cwd(repo_folder):
        return git("rev-parse", "--abbrev-ref", "HEAD").strip()


def has_branch(repo_folder, branch_name) -> bool:
    """
    Checks if a branch exists in the local repository.
    """
    with local.cwd(repo_folder):
        exit_code = git["rev-parse", "--verify", branch_name] & TF
        return exit_code


def has_remote_branch(repo_folder, branch_name, remote) -> bool:
    """
    Checks if a remote branch of a repository exists.
    """
    with local.cwd(repo_folder):
        exit_code = (git["ls-remote", "--heads", remote, branch_name]
                     | grep[branch_name]) & RETCODE
        return exit_code == 0


def branch_has_upstream(repo_folder, branch_name: str,
                        upstream='origin') -> bool:
    """
    Check if a branch has an upstream remote.
    """
    with local.cwd(repo_folder):
        exit_code = (
            git["rev-parse", "--abbrev-ref", branch_name + "@{upstream}"]
            | grep[upstream]) & RETCODE
        return exit_code == 0


def get_download_steps():
    """
    Returns the amount of steps it takes to download VaRA. This can be used to
    track the progress during the long download phase.
    """
    return 6


def download_vara(llvm_source_folder,
                  progress_func=lambda x: None,
                  post_out=lambda x: None):
    """
    Downloads VaRA an all other necessary repos from github.
    """
    dl_counter = 0
    dl_folder = Path(os.path.normpath(llvm_source_folder))

    for project in LLVMProjects:
        progress_func(dl_counter)
        dl_counter += 1
        if project is LLVMProjects.llvm:
            download_repo(
                dl_folder.parent,
                project.url,
                dl_folder.name,
                remote_name=project.remote,
                post_out=post_out)
            add_remote(dl_folder, "origin",
                       "git@github.com:se-passau/vara-llvm.git")
        if project is LLVMProjects.clang_extra:
            download_repo(
                dl_folder / project.path.parent,
                project.url,
                "extra",
                remote_name=project.remote,
                post_out=post_out)
        else:
            download_repo(
                dl_folder / project.path.parent,
                project.url,
                remote_name=project.remote,
                post_out=post_out)
            if project is LLVMProjects.clang:
                add_remote(dl_folder / project.path, "origin",
                           "git@github.com:se-passau/vara-clang.git")

    progress_func(dl_counter)
    mkdir(dl_folder / "build/")
    with local.cwd(dl_folder / "build/"):
        ln("-s", dl_folder / "tools/VaRA/utils/vara/builds/", "build_cfg")


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
    with ProcessManager.create_process("cmake", ["-D" + var_name + "=" + value, "."]) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: run_process_with_output(proc, post_out))


def init_vara_build(path_to_llvm: Path,
                    build_type: BuildType,
                    post_out=lambda x: None):
    """
    Initialize a VaRA build config.
    """
    full_path = path_to_llvm / "build/"
    if not os.path.exists(full_path):
        os.makedirs(full_path)

    if build_type == BuildType.DEV:
        with ProcessManager.create_process("./build_cfg/build-dev.sh", workdir=full_path) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(lambda: run_process_with_output(proc, post_out))


def verify_build_structure(own_libgit: bool,
                           path_to_llvm: Path,
                           post_out=lambda x: None):
    """
    Verify the build strucutre of VaRA:
        - ensure status of submodules
        - update submodules
    """
    if (not get_cmake_var("VARA_BUILD_LIBGIT") or not os.path.exists(
            path_to_llvm / "/tools/VaRA/external/libgit2/CMakeLists.txt")) \
            and own_libgit:
        init_all_submodules(path_to_llvm / LLVMProjects.vara.path)
        update_all_submodules(path_to_llvm / LLVMProjects.vara.path)


def build_vara(path_to_llvm: Path,
               install_prefix: str,
               build_type: BuildType,
               post_out=lambda x: None):
    """
    Builds a VaRA configuration
    """
    own_libgit = bool(CFG["own_libgit2"])
    full_path = path_to_llvm / "build/"
    if build_type == BuildType.DEV:
        full_path /= "dev/"
    if not os.path.exists(full_path):
        try:
            init_vara_build(path_to_llvm, build_type, post_out)
        except ProcessTerminatedError as e:
            shutil.rmtree(full_path)
            raise e

    with local.cwd(full_path):
        verify_build_structure(own_libgit, path_to_llvm, post_out)
        set_vara_cmake_variables(own_libgit, install_prefix, post_out)

    with ProcessManager.create_process("ninja", ["install"], workdir=full_path) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: run_process_with_output(proc, post_out))


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


def get_llvm_project_status(llvm_folder: Path, project_folder="") -> GitStatus:
    """
    Retrieve the git status of a llvm project.
    """
    try:
        with local.cwd(llvm_folder / project_folder):
            fetch_remote('origin')
            git_status = git['status']
            stdout = git_status('-sb')
            for line in stdout.split('\n'):
                if line.startswith('## vara-' + str(CFG['version']) + '-dev'):
                    match = re.match(r".*\[(.*)\]", line)
                    if match is not None:
                        return GitStatus(GitState.BEHIND, match.group(1))
                    return GitStatus(GitState.OK)
    except ProcessTerminatedError:
        pass

    return GitStatus(GitState.ERROR)


def get_vara_status(llvm_folder: Path) -> GitStatus:
    """
    Retrieve the git status of VaRA.
    """
    try:
        with local.cwd(llvm_folder / LLVMProjects.vara.path):
            fetch_remote('origin')
            git_status = git['status']
            stdout = git_status('-sb')
            for line in stdout.split('\n'):
                if line.startswith('## vara-dev'):
                    match = re.match(r".*\[(.*)\]", line)
                    if match is not None:
                        return GitStatus(GitState.BEHIND, match.group(1))
                    return GitStatus(GitState.OK)
    except ProcessTerminatedError:
        pass

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

    def __init__(self, state_signal, path_to_llvm: str):
        super(GitStateChecker, self).__init__()
        self.path_to_llvm = Path(path_to_llvm)
        self.signals = state_signal

    @pyqtSlot()
    def run(self):
        """
        Retrieve status updates for llvm,clang, and VaRA
        """
        llvm_status = get_llvm_project_status(self.path_to_llvm)
        clang_status = get_llvm_project_status(self.path_to_llvm,
                                               LLVMProjects.clang.path)
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
        pull_current_branch(self.llvm_folder / LLVMProjects.clang.path)
        pull_current_branch(self.llvm_folder / LLVMProjects.vara.path)
        self.check_state.possible_state_change.emit()


class ProcessManager:
    __instance = None

    @staticmethod
    @contextmanager
    def create_process(program: str, args: [str] = None, workdir: str = None):
        """
        Creates a new process.
        The does not return immediately. Instead it waits until the process finishes.
        If the process gets interrupted by the user (e.g. by calling the ProcessManager's
        shutdown() method), the ProcessTerminatedError exception gets raised.

        Example usage:

        with ProcessManager.create_process(prog, args) as proc:
            # modify/configure the QProcess object
        # process is started after the when block is exited
        """
        args = [] if args is None else args

        proc = QProcess()
        yield proc

        if workdir is not None:
            with local.cwd(workdir):
                ProcessManager.start_process(proc, program, args)
        else:
            ProcessManager.start_process(proc, program, args)

        proc.waitForFinished(-1)

        if proc.exitStatus() != QProcess.NormalExit:
            raise ProcessTerminatedError()

    @staticmethod
    def getInstance():
        if ProcessManager.__instance == None:
            ProcessManager()
        return ProcessManager.__instance

    @staticmethod
    def start_process(process: QProcess, program: str, args: [str] = None):
        """
        Starts a QProcess object.
        This method returns immediately and does not wait for the process
        to finish."""
        args = [] if args is None else args
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
        with self.__mutex:
            self.__processes = [x for x in self.__processes if x.state() != QProcess.NotRunning]

    def __start_process(self, process: QProcess, program: str, args: [str]):
        with self.__mutex:
            if self.__has_shutdown:
                return
            process.finished.connect(self.__process_finished)
            self.__processes.append(process)
            process.start(program, args)

    def __shutdown(self):
        with self.__mutex:
            self.__has_shutdown = True

    def __terminate_all_processes(self, block=False):
        with self.__mutex:
            for process in self.__processes:
                process.finished.disconnect(self.__process_finished)
                process.kill()
                #process.terminate()
                if block:
                    process.waitForFinished(-1)
            self.__processes.clear()

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

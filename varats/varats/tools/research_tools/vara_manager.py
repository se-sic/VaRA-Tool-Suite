#!/usr/bin/env python3
"""
This module handels the status of VaRA.

Setting up the tooling, keeping it up to date, and providing necessary
information.
"""

import logging
import os
import re
import shutil
import typing as tp
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import RLock

from benchbuild.utils.cmd import cmake, git, grep, ln, mkdir
from plumbum import RETCODE, TF, local
from PyQt5.QtCore import (
    QObject,
    QProcess,
    QRunnable,
    QThreadPool,
    pyqtSignal,
    pyqtSlot,
)

from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.settings import vara_cfg, save_config

LOG = logging.getLogger(__name__)


class LLVMProject():
    """A sub project of LLVM."""

    def __init__(self, name: str, URL: str, remote: str, sub_path: str):
        self.__name = name
        self.__url = URL
        self.__remote = remote
        self.__sub_path = Path(sub_path)

    @property
    def name(self) -> str:
        """Name of the project."""
        return self.__name

    @property
    def url(self) -> str:
        """Repository URL."""
        return self.__url

    @property
    def remote(self) -> str:
        """Git remote."""
        return self.__remote

    @property
    def path(self) -> Path:
        """Path to the project folder within llvm."""
        return self.__sub_path

    def __str__(self) -> str:
        return "{name} [{url}:{remote}] {folder}".format(
            name=self.name, url=self.url, remote=self.remote, folder=self.path
        )


class LLVMProjects(Enum):
    """Mapping of all LLVM projects to paths."""
    llvm = LLVMProject(
        "llvm", "https://git.llvm.org/git/llvm.git", "upstream", ""
    )
    clang = LLVMProject(
        "clang", "https://git.llvm.org/git/clang.git", "upstream", "tools/clang"
    )
    vara = LLVMProject(
        "VaRA", "git@github.com:se-passau/VaRA.git", "origin", "tools/VaRA"
    )
    clang_extra = LLVMProject(
        "clang_extra", "https://git.llvm.org/git/clang-tools-extra.git",
        "upstream", "tools/clang/tools/extra"
    )
    compiler_rt = LLVMProject(
        "compiler-rt", "https://git.llvm.org/git/compiler-rt.git", "upstream",
        "projects/compiler-rt"
    )
    lld = LLVMProject(
        "lld", "https://git.llvm.org/git/lld.git", "upstream", "tools/lld"
    )
    phasar = LLVMProject(
        "phasar", "https://github.com/secure-software-engineering/phasar.git",
        "origin", "tools/phasar"
    )

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def get_project_by_name(project_name: str) -> LLVMProject:
        """
        Get project by name.

        Args:
            project_name: project name
        """
        for proj in iter(LLVMProjects):
            if proj.project_name.lower() == project_name:
                return proj.project
        raise LookupError

    @property
    def project(self) -> LLVMProject:
        """The actual project."""
        if not isinstance(self.value, LLVMProject):
            raise AssertionError()
        return self.value

    @property
    def project_name(self) -> str:
        """Name of the project."""
        return self.project.name

    @property
    def url(self) -> str:
        """Repository URL."""
        return self.project.url

    @property
    def remote(self) -> str:
        """Git remote."""
        return self.project.remote

    @property
    def path(self) -> Path:
        """Path to the project within llvm."""
        return self.project.path

    def is_vara_project(self) -> bool:
        """Checks if this a VaRA controled projected."""
        return self is LLVMProjects.llvm or self is LLVMProjects.clang or\
            self is LLVMProjects.vara

    def is_extra_project(self) -> bool:
        """Checks wether this is an external llvm project."""
        return not self.is_vara_project()


def convert_to_llvmprojects_enum(
    projects_names: tp.List[str]
) -> tp.List[LLVMProjects]:
    """
    Converts a list of strings into a list of LLVMProject.

    Args:
        projects_names: name of the projects to look up
    """
    # Normalize vara naming
    projects_names = ["vara" if x == "VaRA" else x for x in projects_names]

    enum_list = []
    for project_enum in LLVMProjects:
        if project_enum.name in projects_names:
            enum_list.append(project_enum)
            projects_names.remove(project_enum.name)

    if projects_names:
        for project_name in projects_names:
            LOG.warning(
                f"Warning: {project_name} is not a supported project name"
            )

    return enum_list


def generate_full_list_of_llvmprojects() -> tp.List[LLVMProjects]:
    """Generates a list of all LLVM projects."""
    return list(LLVMProjects)


class VaRAProjectsIter():
    """Iterator over vara projects, meaning projects that are modfified to work
    with VaRA."""

    def __init__(self) -> None:
        self.__llvm_project_iter = iter(LLVMProjects)

    def __iter__(self) -> tp.Iterator[LLVMProjects]:
        return self

    def __next__(self) -> LLVMProjects:
        while True:
            val = next(self.__llvm_project_iter)
            if val.is_vara_project():
                return val


def generate_vara_list_of_llvmprojects() -> tp.List[LLVMProjects]:
    """Generates a list of all VaRA llvm projects."""
    return list(VaRAProjectsIter())


class VaRAExtraProjectsIter():
    """Iterator over all additional projects without VaRAs own mofified
    projects."""

    def __init__(self) -> None:
        self.__llvm_project_iter = iter(LLVMProjects)

    def __iter__(self) -> tp.Iterator[LLVMProjects]:
        return self

    def __next__(self) -> LLVMProjects:
        while True:
            val = next(self.__llvm_project_iter)
            if val.is_extra_project():
                return val


def run_process_with_output(
    process: QProcess,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Run a process and forward stdout to a post_out function."""
    output = str(process.readAllStandardOutput().data().decode('utf-8'))
    for line in output.splitlines(True):
        post_out(line)


def download_repo(
    dl_folder: Path,
    url: str,
    repo_name: tp.Optional[str] = None,
    remote_name: tp.Optional[str] = None,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Download a repo into the specified folder."""
    if not dl_folder.exists():
        raise Exception(
            "Could not find download folder  {dl_folder}".format(
                dl_folder=dl_folder
            )
        )

    with local.cwd(dl_folder):
        args = ["clone", "--progress", url]
        if remote_name is not None:
            args.append("--origin")
            args.append(remote_name)

        if repo_name is not None:
            args.append(repo_name)

        with ProcessManager.create_process("git", args) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda: run_process_with_output(proc, post_out)
            )


class BuildType(Enum):
    """This enum contains all VaRA prepared Build configurations."""
    DBG = 1
    DEV = 2
    OPT = 3
    PGO = 4
    DEV_SAN = 5

    def __str__(self) -> str:
        if self == BuildType.DBG:
            return "dbg"
        if self == BuildType.DEV:
            return "dev"
        if self == BuildType.OPT:
            return "opt"
        if self == BuildType.PGO:
            return "PGO"
        if self == BuildType.DEV_SAN:
            return "dev-san"

        raise AssertionError("Unknown build type")

    def build_folder(self) -> Path:
        """Get build type specific buildfolder."""
        return Path(str(self))


def setup_vara(
    init: bool,
    update: bool,
    build: bool,
    llvm_folder: Path,
    install_prefix: str,
    own_libgit: bool,
    include_phasar: bool,
    version: int,
    build_type: BuildType,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Sets up VaRA over cli."""
    vara_cfg()["vara"]["llvm_source_dir"] = str(llvm_folder)
    vara_cfg()["vara"]["llvm_install_dir"] = install_prefix
    save_config()

    use_dev_branches = True

    if init:
        if os.path.exists(llvm_folder):
            print(f"LLVM was already checked out in '{llvm_folder}'.")
        else:
            download_vara(llvm_folder, post_out=post_out)
            checkout_vara_version(
                llvm_folder, include_phasar, version, use_dev_branches
            )
            if own_libgit:
                init_all_submodules(llvm_folder / LLVMProjects.vara.path)
                update_all_submodules(llvm_folder / LLVMProjects.vara.path)

            if include_phasar:
                init_all_submodules(llvm_folder / LLVMProjects.phasar.path)
                update_all_submodules(llvm_folder / LLVMProjects.phasar.path)

    if not os.path.exists(llvm_folder):
        LOG.warning(
            "LLVM was not initialized. Please initialize LLVM with VaRA, "
            "for example, with 'vara-buildsetup -i'."
        )
    else:
        if update:
            if str(vara_cfg()["vara"]["version"]) != str(version):
                for project in LLVMProjects:
                    fetch_repository(llvm_folder / project.path)

                version_name = ""
                version_name += str(version)
                if use_dev_branches:
                    version_name += "-dev"
                checkout_branch(llvm_folder, "vara-" + version_name)
                checkout_branch(
                    llvm_folder / LLVMProjects.clang.path,
                    "vara-" + version_name
                )
                if use_dev_branches:
                    checkout_branch(
                        llvm_folder / LLVMProjects.vara.path, "vara-dev"
                    )

                for project in VaRAExtraProjectsIter():
                    checkout_branch(
                        llvm_folder / project.path, "release_" + str(version)
                    )

                vara_cfg()["vara"]["version"] = int(version)
                save_config()

            pull_current_branch(llvm_folder)
            pull_current_branch(llvm_folder / LLVMProjects.clang.path)
            pull_current_branch(llvm_folder / LLVMProjects.vara.path)
            if own_libgit:
                update_all_submodules(llvm_folder / LLVMProjects.vara.path)

            if include_phasar:
                pull_current_branch(llvm_folder / LLVMProjects.phasar.path)
                update_all_submodules(llvm_folder / LLVMProjects.phasar.path)

        if build:
            build_vara(
                llvm_folder,
                install_prefix=install_prefix,
                build_type=build_type,
                post_out=post_out
            )


def add_remote(repo_folder: Path, remote: str, url: str) -> None:
    """Adds new remote to the repository."""
    with ProcessManager.create_process(
        "git", ["remote", "add", remote, url], workdir=repo_folder
    ):
        pass


def show_status(repo_folder: Path) -> None:
    """Show git status."""
    with local.cwd(repo_folder):
        git["status"].run_fg()


def get_branches(
    repo_folder: Path, extra_args: tp.Optional[tp.List[str]] = None
) -> str:
    """Show git branches."""
    extra_args = [] if extra_args is None else extra_args

    args = ["branch"]
    args += extra_args

    with local.cwd(repo_folder):
        return tp.cast(str, git(args))


def fetch_remote(
    remote: tp.Optional[str] = None,
    repo_folder: tp.Optional[Path] = None,
    extra_args: tp.Optional[tp.List[str]] = None
) -> None:
    """Fetches the new changes from the remote."""
    extra_args = [] if extra_args is None else extra_args

    args = ["fetch"]
    args += extra_args
    if remote:
        args.append(remote)

    with ProcessManager.create_process("git", args, workdir=repo_folder):
        pass


def init_all_submodules(folder: Path) -> None:
    """Inits all submodules."""
    with ProcessManager.create_process(
        "git", ["submodule", "init"], workdir=folder
    ):
        pass


def update_all_submodules(folder: Path, recursive: bool = True) -> None:
    """Updates all submodules."""
    git_params = ["submodule", "update"]
    if recursive:
        git_params.append("--recursive")

    with ProcessManager.create_process("git", git_params, workdir=folder):
        pass


def pull_current_branch(repo_folder: tp.Optional[Path] = None) -> None:
    """Pull in changes in a certain branch."""
    with ProcessManager.create_process("git", ["pull"], workdir=repo_folder):
        pass


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
        with local.cwd(repo_folder):
            git(cmd_args)


def fetch_repository(repo_folder: tp.Optional[Path] = None) -> None:
    """Pull in changes in a certain branch."""
    with ProcessManager.create_process("git", ["fetch"], workdir=repo_folder):
        pass


def checkout_branch(repo_folder: Path, branch: str) -> None:
    """Checks out a branch in the repository."""
    with ProcessManager.create_process(
        "git", ["checkout", branch], workdir=repo_folder
    ):
        pass


def checkout_new_branch(
    repo_folder: Path,
    branch: str,
    remote_branch: tp.Optional[str] = None
) -> None:
    """Checks out a new branch in the repository."""
    args = ["checkout", "-b", branch]
    if remote_branch is not None:
        args.append(remote_branch)
    with ProcessManager.create_process("git", args, workdir=repo_folder):
        pass


def get_current_branch(repo_folder: tp.Optional[Path]) -> str:
    """Get the current branch of a repository, e.g., HEAD."""
    if repo_folder is None or repo_folder == Path(''):
        return tp.cast(str, git("rev-parse", "--abbrev-ref", "HEAD").strip())

    with local.cwd(repo_folder):
        return tp.cast(str, git("rev-parse", "--abbrev-ref", "HEAD").strip())


def has_branch(repo_folder: Path, branch_name: str) -> bool:
    """Checks if a branch exists in the local repository."""
    with local.cwd(repo_folder):
        exit_code = git["rev-parse", "--verify", branch_name] & TF
        return tp.cast(bool, exit_code)


def has_remote_branch(repo_folder: Path, branch_name: str, remote: str) -> bool:
    """Checks if a remote branch of a repository exists."""
    with local.cwd(repo_folder):
        exit_code = (
            git["ls-remote", "--heads", remote, branch_name] | grep[branch_name]
        ) & RETCODE
        return tp.cast(bool, exit_code == 0)


def branch_has_upstream(
    repo_folder: Path, branch_name: str, upstream: str = 'origin'
) -> bool:
    """Check if a branch has an upstream remote."""
    with local.cwd(repo_folder):
        exit_code = (
            git["rev-parse", "--abbrev-ref", branch_name + "@{upstream}"] |
            grep[upstream]
        ) & RETCODE
        return tp.cast(bool, exit_code == 0)


def get_download_steps() -> int:
    """
    Returns the amount of steps it takes to download VaRA.

    This can be used to track the progress during the long download phase.
    """
    return 6


def download_vara(
    llvm_source_folder: Path,
    progress_func: tp.Callable[[int], None] = lambda x: None,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Downloads VaRA an all other necessary repos from github."""
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
                post_out=post_out
            )
            add_remote(
                dl_folder, "origin", "git@github.com:se-passau/vara-llvm.git"
            )
            fetch_remote("origin", dl_folder)
        if project is LLVMProjects.clang_extra:
            download_repo(
                dl_folder / project.path.parent,
                project.url,
                "extra",
                remote_name=project.remote,
                post_out=post_out
            )
        else:
            download_repo(
                dl_folder / project.path.parent,
                project.url,
                remote_name=project.remote,
                post_out=post_out
            )
            if project is LLVMProjects.clang:
                add_remote(
                    dl_folder / project.path, "origin",
                    "git@github.com:se-passau/vara-clang.git"
                )
                fetch_remote("origin", dl_folder / project.path)

    progress_func(dl_counter)
    mkdir(dl_folder / "build/")
    with local.cwd(dl_folder / "build/"):
        ln("-s", dl_folder / "tools/VaRA/utils/vara/builds/", "build_cfg")


def checkout_vara_version(
    llvm_folder: Path, include_phasar: bool, version: int, dev: bool
) -> None:
    """
    Checks out all related repositories to match the VaRA version number.

    ../llvm/ 60 dev
    """
    version_name = ""
    version_name += str(version)
    if dev:
        version_name += "-dev"

    checkout_new_branch(
        llvm_folder, "vara-" + version_name, "origin/vara-" + version_name
    )
    checkout_new_branch(
        llvm_folder / "tools/clang/", "vara-" + version_name,
        "origin/vara-" + version_name
    )
    if dev:
        checkout_branch(llvm_folder / "tools/VaRA/", "vara-dev")

    checkout_branch(
        llvm_folder / "tools/clang/tools/extra/", "release_" + str(version)
    )
    checkout_branch(llvm_folder / "tools/lld/", "release_" + str(version))
    checkout_branch(
        llvm_folder / "projects/compiler-rt/", "release_" + str(version)
    )
    if include_phasar:
        checkout_branch(llvm_folder / LLVMProjects.phasar.path, "development")


def get_cmake_var(var_name: str) -> bool:
    """Fetch the value of a cmake variable from the current cmake config."""
    for line in iter(cmake("-LA", "-N", "CMakeLists.txt").splitlines()):
        if var_name not in line:
            continue
        return tp.cast(bool, line.split("=")[1] == "ON")
    return False


def set_cmake_var(
    var_name: str,
    value: str,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Sets a cmake variable in the current cmake config."""
    with ProcessManager.create_process(
        "cmake", ["-D" + var_name + "=" + value, "."]
    ) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: run_process_with_output(proc, post_out)
        )


def init_vara_build(
    path_to_llvm: Path,
    build_type: BuildType,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Initialize a VaRA build config."""
    full_path = path_to_llvm / "build/"
    if not os.path.exists(full_path):
        os.makedirs(full_path)

    build_script = "./build_cfg/build-{build_type}.sh".format(
        build_type=str(build_type)
    )

    with ProcessManager.create_process(build_script, workdir=full_path) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: run_process_with_output(proc, post_out)
        )


def verify_build_structure(
    own_libgit: bool, include_phasar: bool, path_to_llvm: Path
) -> None:
    """
    Verify the build strucutre of VaRA:

        - ensure status of submodules
        - update submodules

    Args:
        own_libgit: ``True``, if own libgit should be self build
        include_phasar: ``True``, if phasar should be included in build
    """
    if (not get_cmake_var("VARA_BUILD_LIBGIT") or not os.path.exists(
            path_to_llvm / "/tools/VaRA/external/libgit2/CMakeLists.txt")) \
            and own_libgit:
        init_all_submodules(path_to_llvm / LLVMProjects.vara.path)
        update_all_submodules(path_to_llvm / LLVMProjects.vara.path)

    if include_phasar:
        init_all_submodules(path_to_llvm / LLVMProjects.phasar.path)
        update_all_submodules(path_to_llvm / LLVMProjects.phasar.path)


def build_vara(
    path_to_llvm: Path,
    install_prefix: str,
    build_type: BuildType,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Builds a VaRA configuration."""
    own_libgit = bool(vara_cfg()["vara"]["own_libgit2"])
    include_phasar = bool(vara_cfg()["vara"]["with_phasar"])
    full_path = path_to_llvm / "build/"
    full_path /= build_type.build_folder()

    if not os.path.exists(full_path):
        try:
            init_vara_build(path_to_llvm, build_type, post_out)
        except ProcessTerminatedError as error:
            shutil.rmtree(full_path)
            raise error

    with local.cwd(full_path):
        verify_build_structure(own_libgit, include_phasar, path_to_llvm)

        set_vara_cmake_variables(install_prefix, post_out)

    with ProcessManager.create_process(
        "ninja", ["install"], workdir=full_path
    ) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: run_process_with_output(proc, post_out)
        )


def set_vara_cmake_variables(
    install_prefix: str,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Set all wanted/needed cmake flags."""
    set_cmake_var("CMAKE_INSTALL_PREFIX", install_prefix, post_out)


###############################################################################
# Git Handling
###############################################################################


class GitState(Enum):
    """Represent the direct state of a branch."""
    OK = 1
    BEHIND = 2
    ERROR = 3


class GitStatus():
    """Represents the current update status of a git repository."""

    def __init__(self, state: GitState, msg: str = "") -> None:
        self.__state = state
        self.__msg = msg

    @property
    def state(self) -> GitState:
        """Current state of the git."""
        return self.__state

    @property
    def msg(self) -> str:
        """Additional msg."""
        return self.__msg

    def __str__(self) -> str:
        if self.state == GitState.OK:
            return "OK"
        if self.state == GitState.BEHIND:
            return self.msg
        return "Error"


def get_llvm_project_status(
    llvm_folder: Path, project_folder: str = ""
) -> GitStatus:
    """Retrieve the git status of a llvm project."""
    try:
        with local.cwd(llvm_folder / project_folder):
            fetch_remote('origin')
            git_status = git['status']
            stdout = git_status('-sb')
            for line in stdout.split('\n'):
                if line.startswith(
                    '## vara-' + str(vara_cfg()['version']) + '-dev'
                ):
                    match = re.match(r".*\[(.*)\]", line)
                    if match is not None:
                        return GitStatus(GitState.BEHIND, match.group(1))
                    return GitStatus(GitState.OK)
    except ProcessTerminatedError:
        pass

    return GitStatus(GitState.ERROR)


def get_vara_status(llvm_folder: Path) -> GitStatus:
    """Retrieve the git status of VaRA."""
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
    """GitStateSignals to send state update to the GUI."""
    status_update = pyqtSignal(object, object, object)


class CheckStateSignal(QObject):
    """This signal is emited when the state could have changed."""
    possible_state_change = pyqtSignal()


class GitStateChecker(QRunnable):
    """GitStateChecker to fetch and verify the git status."""

    def __init__(
        self, state_signal: GitStateSignals, path_to_llvm: Path
    ) -> None:
        super().__init__()
        self.path_to_llvm = path_to_llvm
        self.signals = state_signal

    @pyqtSlot()
    def run(self) -> None:
        """Retrieve status updates for llvm,clang, and VaRA."""
        llvm_status = get_llvm_project_status(self.path_to_llvm)
        clang_status = get_llvm_project_status(
            self.path_to_llvm, str(LLVMProjects.clang.path)
        )
        vara_status = get_vara_status(self.path_to_llvm)

        self.signals.status_update.emit(llvm_status, clang_status, vara_status)


class PullWorker(QRunnable):
    """QtWorker to update repositories."""

    def __init__(self, llvm_folder: Path) -> None:
        super().__init__()
        self.llvm_folder = llvm_folder
        self.check_state = CheckStateSignal()

    @pyqtSlot()
    def run(self) -> None:
        """Pull changes and update the current branch."""
        pull_current_branch(self.llvm_folder)
        pull_current_branch(self.llvm_folder / LLVMProjects.clang.path)
        pull_current_branch(self.llvm_folder / LLVMProjects.vara.path)
        self.check_state.possible_state_change.emit()


class ProcessManager():
    """Manager of a pool of background processes that are designed to handle
    different tasks in parallel."""

    __instance: tp.Optional['ProcessManager'] = None

    @staticmethod
    @contextmanager
    def create_process(
        program: str,
        args: tp.Optional[tp.List[str]] = None,
        workdir: tp.Optional[tp.Union[str, Path]] = None
    ) -> tp.Iterator[QProcess]:
        """
        Creates a new process. The method does not return immediately. Instead
        it waits until the process finishes. If the process gets interrupted by
        the user (e.g. by calling the ProcessManager's shutdown() method), the
        ProcessTerminatedError exception gets raised.

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
    def get_instance() -> 'ProcessManager':
        """Get access to the ProcessManager."""
        if ProcessManager.__instance is None:
            ProcessManager()
        if ProcessManager.__instance is None:
            raise Exception("ProcessManager was not initialized")
        if not isinstance(ProcessManager.__instance, ProcessManager):
            raise AssertionError()
        return ProcessManager.__instance

    @staticmethod
    def start_process(
        process: QProcess,
        program: str,
        args: tp.Optional[tp.List[str]] = None
    ) -> None:
        """
        Starts a QProcess object.

        This method returns immediately and does not wait for the process to
        finish.
        """
        args = [] if args is None else args
        # pylint: disable=protected-access
        ProcessManager.get_instance().__start_process(process, program, args)

    @staticmethod
    def shutdown() -> None:
        """Shuts down the `ProcessManager` and terminates all processes."""
        # pylint: disable=protected-access
        inst = ProcessManager.get_instance()
        with inst.__mutex:
            inst.__shutdown()
            inst.__terminate_all_processes(block=False)

    @staticmethod
    def terminate_all_processes(block: bool = False) -> None:
        """Terminates all running processes tracked by the ProcessManager."""
        # pylint: disable=protected-access
        ProcessManager.get_instance().__terminate_all_processes(block)

    def __init__(self) -> None:
        if ProcessManager.__instance is not None:
            raise Exception("This class is a singleton!")

        ProcessManager.__instance = self

        self.__has_shutdown = False
        self.__processes: tp.List[QProcess] = []
        self.__mutex = RLock()

    def __process_finished(self) -> None:
        with self.__mutex:
            self.__processes = [
                x for x in self.__processes if x.state() != QProcess.NotRunning
            ]

    def __start_process(
        self, process: QProcess, program: str, args: tp.List[str]
    ) -> None:
        with self.__mutex:
            if self.__has_shutdown:
                return
            process.finished.connect(self.__process_finished)
            self.__processes.append(process)
            process.start(program, args)

    def __shutdown(self) -> None:
        with self.__mutex:
            self.__has_shutdown = True

    def __terminate_all_processes(self, block: bool = False) -> None:
        with self.__mutex:
            for process in self.__processes:
                process.finished.disconnect(self.__process_finished)
                process.kill()
                # process.terminate()
                if block:
                    process.waitForFinished(-1)
            self.__processes.clear()

    def __del__(self) -> None:
        with self.__mutex:
            self.__shutdown()
            self.__terminate_all_processes(block=False)


class VaRAStateManager():
    """Manages the current installation of VaRA."""

    def __init__(self, llvm_folder: Path) -> None:
        if not llvm_folder.exists():
            raise ValueError("llvm_folder path did not exist!")

        self.llvm_folder = llvm_folder
        self.state_signal = GitStateSignals()

        self.thread_pool = QThreadPool()

    def change_llvm_source_folder(self, llvm_folder: Path) -> None:
        """Change the current llvm source folder."""
        self.llvm_folder = llvm_folder

    def check_repo_state(self) -> None:
        """Check the state of the three VaRA repos."""
        worker = GitStateChecker(self.state_signal, self.llvm_folder)
        self.thread_pool.start(worker)

    def update_current_branch(self) -> None:
        """Update the current branches of the VaRA setup."""
        worker = PullWorker(self.llvm_folder)
        worker.check_state.possible_state_change.connect(self.check_repo_state)
        self.thread_pool.start(worker)

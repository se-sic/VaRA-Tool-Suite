#!/usr/bin/env python3
"""
This module handels the status of VaRA.

Setting up the tooling, keeping it up to date, and providing necessary
information.
"""

import logging
import re
import typing as tp
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from threading import RLock

from benchbuild.utils.cmd import git
from plumbum import local
from PyQt5.QtCore import QProcess

from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.git_commands import fetch_remote
from varats.utils.settings import vara_cfg

LOG = logging.getLogger(__name__)


def run_process_with_output(
    process: QProcess,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Run a process and forward stdout to a post_out function."""
    output = str(process.readAllStandardOutput().data().decode('utf-8'))
    for line in output.splitlines(True):
        post_out(line)


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

    def build_folder(self, suffix: tp.Optional[str] = None) -> Path:
        """
        Get build type specific buildfolder.

        Args:
            suffix: an optional suffix to append to the build folder name

        Test:
        >>> str(BuildType.DBG.build_folder())
        'dbg'
        >>> str(BuildType.DEV.build_folder("foo"))
        'dev_foo'
        """
        if suffix:
            return Path(f"{str(self)}_{suffix}")
        return Path(str(self))


###############################################################################
# Git Handling
###############################################################################


class GitState(Enum):
    """Represent the direct state of a branch."""
    value: int

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


###############################################################################
# Qt interaction hanlders
###############################################################################


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

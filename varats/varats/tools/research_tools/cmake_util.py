"""CMake utilities."""

import typing as tp

from benchbuild.utils.cmd import cmake
from PyQt5.QtCore import QProcess

from varats.tools.research_tools.vara_manager import (
    ProcessManager,
    run_process_with_output,
)


def is_cmake_var_set(var_name: str) -> bool:
    """
    Check if a specific cmake variable is set to ON.

    Args:
        var_name: of the cmake variable

    Returns: true, if the cmake variable is set
    """
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
    """
    Sets a cmake variable in the current cmake config.

    Args:
        var_name: of the cmake variable
        value: to set
        post_out: callback to write console output to
    """
    with ProcessManager.create_process(
        "cmake", ["-D" + var_name + "=" + value, "."]
    ) as proc:
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: run_process_with_output(proc, post_out)
        )

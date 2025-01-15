import socket
import typing as tp

from benchbuild import Project
from benchbuild.utils import actions
from plumbum import local
from plumbum.cmd import kill


class CompileWithBlameServer(actions.Compile):  # type: ignore
    """Start blame server before and kill server after compilation."""

    NAME = "BlameServerSteps"
    DESCRIPTION = "Start server before and kill server after compilation."

    def __init__(self, project: Project, port: int):
        super().__init__(project)
        self.__port = port

    def __call__(self) -> actions.StepResult:
        server_cmd = local["vara-blamed"][
            f"--blame-server=0.0.0.0:{self.__port}"]
        server_proc = server_cmd.popen()
        step_result = actions.StepResult.ERROR
        try:
            step_result = super().__call__()
        finally:
            kill[str(server_proc.pid)]()

        return step_result

    @staticmethod
    def find_open_port() -> tp.Any:
        """Finds and returns an available port on the local machine."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to a free port provided by the OS
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

"""
Implements blame experiment using a blame cache server.

The experiment starts the blame server, compiles with blame annotations and
kills the server at the end.
"""
import socket
import typing as tp

from benchbuild import Project
from benchbuild.utils import actions
from plumbum import local
from plumbum.cmd import kill

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_annotations import BlameAnnotations as BA
from varats.experiment.experiment_util import (
    VersionExperiment,
    create_default_compiler_error_handler,
)
from varats.experiment.wllvm import BCFileExtensions, Extract
from varats.experiments.vara.blame_ast_experiment import (
    BlameAnnotationGeneration,
)
from varats.report.report import ReportSpecification


class BlameServerSteps(actions.Compile):  # type: ignore
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
        steps = actions.StepResult(3)
        try:
            steps = super().__call__()
        finally:
            kill[str(server_proc.pid)]()

        return steps

    @staticmethod
    def find_open_port() -> tp.Any:
        """Finds and returns an available port on the local machine."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to a free port provided by the OS
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]


class BlameServerExperiment(VersionExperiment, shorthand="BSE"):
    """Generate a blame annotation report using blame server."""

    NAME = "RunBlameServer"

    REPORT_SPEC = ReportSpecification(BA)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME  #TODO: add extension for blame server ?
        ]

        BE.setup_basic_blame_experiment(self, project, BA)
        open_port = BlameServerSteps.find_open_port()
        project.cflags += [f"-fvara-blame-server=0.0.0.0:{open_port}"]
        analysis_actions = []
        analysis_actions.append(BlameServerSteps(project, open_port))
        analysis_actions.append(
            Extract(
                project,
                bc_file_extensions,
                handler=create_default_compiler_error_handler(
                    self.get_handle(), project, self.REPORT_SPEC.main_report
                )
            )
        )
        analysis_actions.append(
            BlameAnnotationGeneration(
                project, self.get_handle(), bc_file_extensions
            )
        )

        return analysis_actions

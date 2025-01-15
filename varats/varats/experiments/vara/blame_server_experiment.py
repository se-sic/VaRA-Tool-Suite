"""
Implements blame experiment using a blame cache server.

The experiment starts the blame server, compiles with blame annotations and
kills the server at the end.
"""
import typing as tp

from benchbuild import Project
from benchbuild.utils import actions

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_annotations import BlameAnnotations as BA
from varats.experiment.experiment_util import (
    VersionExperiment,
    create_default_compiler_error_handler,
)
from varats.experiment.steps.blame_server import CompileWithBlameServer
from varats.experiment.wllvm import BCFileExtensions, Extract
from varats.experiments.vara.blame_ast_experiment import (
    BlameAnnotationGeneration,
)
from varats.report.report import ReportSpecification


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
            BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
            BCFileExtensions.BLAME
        ]

        BE.setup_basic_blame_experiment(self, project, BA)
        open_port = CompileWithBlameServer.find_open_port()
        project.cflags += [f"-fvara-blame-server=0.0.0.0:{open_port}"]
        analysis_actions = []
        analysis_actions.append(CompileWithBlameServer(project, open_port))
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

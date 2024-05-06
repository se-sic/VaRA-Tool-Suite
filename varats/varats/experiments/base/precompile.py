"""Implements an experiment that stores compiled binaries."""
import logging
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild import Project
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.utils.cmd import cp

from varats.data.reports.compiled_binary_report import CompiledBinaryReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    exec_func_with_pe_error_handler,
    get_default_compile_error_wrapped,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.experiment.wllvm import RunWLLVM
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification, ReportFilename
from varats.revision.revisions import get_processed_revisions_files

LOG = logging.getLogger(__name__)


class StoreBinaries(actions.ProjectStep):  # type: ignore
    """Store a compiled binary."""

    NAME = "StoreBinaries"
    DESCRIPTION = "Stores compiled binaries."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """Store binaries as reports."""

        for binary in self.project.binaries:
            report_path = create_new_success_result_filepath(
                self.__experiment_handle, CompiledBinaryReport, self.project,
                binary
            )

            run_cmd = cp[Path(self.project.source_of_primary, binary.path),
                         report_path]

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, CompiledBinaryReport
                )
            )

        return actions.StepResult.OK


class RestoreBinaries(actions.ProjectStep):  # type: ignore
    """Restore compiled binaries to the current experiment context."""

    NAME = "RestoreBinaries"
    DESCRIPTION = "Restores precompiled binaries."

    project: VProject

    def __init__(
        self, project: Project, experiment_type: tp.Type[VersionExperiment]
    ):
        super().__init__(project=project)
        self.__experiment_type = experiment_type

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """Restore binaries from reports."""

        for binary in self.project.binaries:

            def filter_reports(file_name: str) -> bool:
                return ReportFilename(
                    file_name
                ).commit_hash.hash != self.project.version_of_primary

            report_path = get_processed_revisions_files(
                self.project.name,
                self.__experiment_type,
                file_name_filter=filter_reports
            )[0]

            if not report_path.full_path().exists():
                LOG.error("Could not find report file for binary.")
                return actions.StepResult.ERROR

            binary_path = Path(self.project.source_of_primary, binary.path)
            if not binary_path.parent.exists():
                binary_path.parent.mkdir(parents=True)

            bb.watch(cp[report_path, binary_path])()

        return actions.StepResult.OK


class PreCompile(VersionExperiment, shorthand="PREC"):
    """Stores compiled binaries as reports."""

    NAME = "PreCompile"

    REPORT_SPEC = ReportSpecification(CompiledBinaryReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = [
            actions.Compile(project),
            StoreBinaries(project, self.get_handle()),
            actions.Clean(project)
        ]

        return analysis_actions

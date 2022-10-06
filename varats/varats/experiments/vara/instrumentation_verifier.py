"""Experiment that instruments a project with verification instrumentation that
is used during execution to check if regions are correctly opend/closed."""
import os
import textwrap
import typing as tp
from pathlib import Path

import benchbuild.command as bbcmd
from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.instrumentation_verifier_report import (
    InstrVerifierReport,
)
from varats.experiment.experiment_util import (
    ExperimentHandle,
    create_new_success_result_filepath,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
    ZippedReportFolder,
)
from varats.experiment.wllvm import (
    RunWLLVM,
    BCFileExtensions,
    get_bc_cache_actions,
)
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.report import FileStatusExtension as FSE
from varats.utils.git_util import ShortCommitHash

# TODO: merge this with feature runner experiment


class RunAndVerifyInstrumentedProject(actions.ProjectStep):  # type: ignore
    """Experiment step that executes a traced binary, extracing information from
    the run-time analysis."""

    NAME = "RunAndVerifyInstrumentedProject"
    DESCRIPTION = "foo"

    project: VProject

    def __init__(
        self, project: VProject, experiment_handle: ExperimentHandle
    ) -> None:
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.run_verifier()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumentation verifier", indent * " "
        )

    def run_verifier(self) -> actions.StepResult:
        """Runs the binary with the embedded region verifier code."""

        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                # Skip libaries as we cannot run them
                continue

            result_filepath = create_new_success_result_filepath(
                self.__experiment_handle,
                self.__experiment_handle.report_spec().main_report,
                self.project, binary
            )

            with local.cwd(local.path(self.project.builddir)):
                with ZippedReportFolder(result_filepath.full_path()) as tmp_dir:
                    for prj_command in workload_commands(
                        self.project, binary, [WorkloadCategory.EXAMPLE]
                    ):
                        local_tracefile_path = Path(
                            tmp_dir
                        ) / f"trace_{prj_command.command.label}.json"
                        with local.env(VARA_TRACE_FILE=local_tracefile_path):
                            pb_cmd = prj_command.command.as_plumbum(
                                project=self.project
                            )
                            print(
                                f"Running example {prj_command.command.label}"
                            )
                            with cleanup(prj_command):
                                pb_cmd()

                        # TODO: figure out how to handle different configs
                        # executable("--slow")
                        # executable()

        return actions.StepResult.OK


class RunInstrVerifier(FeatureExperiment, shorthand="RIV"):
    """Test runner for feature performance."""

    NAME = "RunInstrVerifier"

    REPORT_SPEC = ReportSpecification(InstrVerifierReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = "instr_verify"

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(instr_type, True)

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self)

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunAndVerifyInstrumentedProject(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

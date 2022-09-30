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


class RunInstrVerifier(VersionExperiment, shorthand="RIV"):
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

        fm_provider = FeatureModelProvider.create_provider_for_project(
            type(project)
        )
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        # Sets FM model flags
        project.cflags += [
            "-fvara-feature", f"-fvara-fm-path={fm_path.absolute()}"
        ]
        # Sets vara tracing flags
        project.cflags += [
            "-fsanitize=vara", f"-fvara-instr={instr_type}", "-flto",
            "-fuse-ld=lld", "-Wl,-plugin-opt=save-temps",
            "-flegacy-pass-manager"
        ]
        project.ldflags += ["-flto"]

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

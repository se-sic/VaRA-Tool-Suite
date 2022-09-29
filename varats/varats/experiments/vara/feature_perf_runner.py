"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import os
import typing as tp

from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.experiment.experiment_util import (
    ExperimentHandle,
    get_varats_result_folder,
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
)
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReport
from varats.utils.git_util import ShortCommitHash


class ExecAndTraceBinary(actions.ProjectStep):  # type: ignore
    """Executes the specified binaries of the project, in specific
    configurations, against one or multiple workloads."""

    NAME = "ExecBinary"
    DESCRIPTION = "Executes each binary and caputres white-box " +\
        "performance traces."

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.run_perf_tracing()

    def run_perf_tracing(self) -> actions.StepResult:
        """Execute the specified binaries of the project, in specific
        configurations, against one or multiple workloads."""
        print(f"PWD {os.getcwd()}")

        vara_result_folder = get_varats_result_folder(self.project)
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            result_file = create_new_success_result_filepath(
                self.__experiment_handle, TEFReport, self.project, binary
            )

            with local.cwd(local.path(self.project.source_of_primary)):
                print(
                    f"Currenlty at {local.path(self.project.source_of_primary)}"
                )
                print(f"Bin path {binary.path}")

                # executable = local[f"{binary.path}"]

                with local.env(
                    VARA_TRACE_FILE=f"{vara_result_folder}/{result_file}"
                ):

                    workload = "/tmp/countries-land-1km.geo.json"

                    # TODO: figure out how to handle workloads
                    binary("-k", workload)

                    # TODO: figure out how to handle different configs
                    # executable("--slow")
                    # executable()

        return actions.StepResult.OK


class FeaturePerfRunner(VersionExperiment, shorthand="FPR"):
    """Test runner for feature performance."""

    NAME = "RunFeaturePerf"

    REPORT_SPEC = ReportSpecification(TEFReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = "instr_verify"  # trace_event

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
            "-fuse-ld=lld"
        ]
        project.ldflags += ["-flto"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << run.WithTimeout()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(ExecAndTraceBinary(project, self.get_handle()))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

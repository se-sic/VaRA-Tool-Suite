"""Base class experiment and utilities for experiments that work with
features."""
import textwrap
import typing as tp
from abc import abstractmethod
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.project import Project
from benchbuild.utils.actions import Step, ProjectStep, StepResult
from plumbum import local

from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    create_new_success_result_filepath,
    ZippedReportFolder,
)
from varats.experiment.workload_util import workload_commands, WorkloadCategory
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelProvider,
    FeatureModelNotFound,
)
from varats.report.report import ReportSpecification


class FeatureExperiment(VersionExperiment, shorthand=""):
    """Base class experiment for feature specific experiments."""

    NAME = "FeatureExperiment"

    REPORT_SPEC = ReportSpecification()

    @abstractmethod
    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    @staticmethod
    def get_feature_model_path(project: VProject) -> Path:
        """Get access to the feature model for a given project."""
        fm_provider = FeatureModelProvider.create_provider_for_project(
            type(project)
        )
        if fm_provider is None:
            raise Exception("Could not get FeatureModelProvider!")

        fm_path = fm_provider.get_feature_model_path(project.version_of_primary)
        if fm_path is None or not fm_path.exists():
            raise FeatureModelNotFound(project, fm_path)

        return fm_path

    @staticmethod
    def get_vara_feature_cflags(project: VProject) -> tp.List[str]:
        """
        Returns the cflags needed to enable VaRAs feature support, i.e., passing
        the compiler a feature model and lowering the feature information into
        the LLVM-IR.

        Args:
            project: to get the cflags for

        Returns: list of feature cflags
        """
        fm_path = FeatureExperiment.get_feature_model_path(project).absolute()
        return ["-fvara-feature", f"-fvara-fm-path={fm_path}"]

    @staticmethod
    def get_vara_tracing_cflags(instr_type: str,
                                save_temps: bool = False) -> tp.List[str]:
        """
        Returns the cflags needed to trace projects with VaRA, using the
        specified tracer code.

        Args:
            instr_type: instrumentation type to use
            save_temps: saves temporary LLVM-IR files (good for debugging)

        Returns: list of tracing specific cflags
        """
        c_flags = [
            "-fsanitize=vara", f"-fvara-instr={instr_type}", "-flto",
            "-fuse-ld=lld", "-flegacy-pass-manager"
        ]
        if save_temps:
            c_flags += ["-Wl,-plugin-opt=save-temps"]

        return c_flags

    @staticmethod
    def get_vara_tracing_ldflags() -> tp.List[str]:
        """
        Returns the ldflags needed to instrument projects with VaRA during LTO.

        Returns: ldflags for VaRA LTO support
        """
        return ["-flto"]


class RunVaRATracedWorkloads(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> StepResult:
        return self.run_traced_code()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumentation verifier", indent * " "
        )

    def run_traced_code(self) -> StepResult:
        """Runs the binary with the embedded tracing code."""
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

        return StepResult.OK

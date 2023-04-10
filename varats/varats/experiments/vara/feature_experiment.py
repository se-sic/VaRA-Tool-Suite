"""Base class experiment and utilities for experiments that work with
features."""
import json
import re
import textwrap
import typing as tp
from abc import abstractmethod
from enum import Enum
from pathlib import Path

from benchbuild.command import cleanup
from benchbuild.extensions import compiler, run, time
from benchbuild.utils.actions import (
    ProjectStep,
    Step,
    StepResult,
    Compile,
    Clean,
)
from plumbum import local

from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_current_config_id,
    get_default_compile_error_wrapped,
    get_extra_config_options,
    WithUnlimitedStackSize,
)
from varats.experiment.trace_util import merge_trace
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.feature.feature_model_provider import (
    FeatureModelNotFound,
    FeatureModelProvider,
)
from varats.report.report import ReportSpecification


class FeatureInstrType(Enum):
    """Type of instrumentation to be used in feature tracing ."""

    NONE = ""
    """Don't add any instrumentation."""

    PRINT = "print"
    """Print tracing information to stdout."""

    PERF_INFLUENCE_TRACE = "perf_infl_trace"
    """Produce a performance influence trace file"""

    TEF = "trace_event"
    """Produce a trace file."""

    USDT = "usdt"
    """Insert USDT probes."""

    USDT_RAW = "usdt_raw"
    """Insert raw USDT probes."""

    VERIFY = "instr_verify"
    """Verify markers."""


class FeatureExperiment(VersionExperiment, shorthand=""):
    """Base class experiment for feature specific experiments."""

    NAME = "FeatureExperiment"

    REPORT_SPEC = ReportSpecification()

    @abstractmethod
    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        """Get the actions a project wants to run."""

    def get_common_tracing_actions(
        self,
        project: VProject,
        instr_type: FeatureInstrType,
        analysis_actions: tp.List[Step],
        save_temps: bool = False,
        instruction_threshold: tp.Optional[int] = None,
    ) -> tp.MutableSequence[Step]:
        """
        Set common options and return a list of common actions for feature
        tracing experiments.

        Args:
            project: to analyze instr_type: type of the instrumentation to add
            instr_type: type of instrumentation to add analysis_actions:
            analysis actions to perform save_temps: saves temporary LLVM-IR
            files (good for debugging) instruction_threshold: minimum function
            size to instrument

        Returns:
            list of actions for project containing compile, analysis_actions,
            and clean
        """
        project.cflags += self.get_vara_feature_cflags(project)
        project.cflags += self.get_vara_tracing_cflags(
            instr_type, save_temps, instruction_threshold=instruction_threshold
        )
        project.ldflags += self.get_vara_tracing_ldflags()

        # runtime and compiler extensions
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize()

        # project actions
        project_actions = []
        project_actions.append(Compile(project))
        project_actions.extend(analysis_actions)
        project_actions.append(Clean(project))

        # compile error handler
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project,
            self.report_spec().main_report
        )

        return project_actions

    @staticmethod
    def get_feature_model_path(project: VProject) -> Path:
        """Get access to the feature model for a given project."""
        fm_provider = FeatureModelProvider.create_provider_for_project(
            type(project)
        )
        if fm_provider is None:
            raise RuntimeError("Could not get FeatureModelProvider!")

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
        try:
            fm_path = FeatureExperiment.get_feature_model_path(project
                                                              ).absolute()
            return ["-fvara-feature", f"-fvara-fm-path={fm_path}"]
        except FeatureModelNotFound:
            return ["-fvara-feature", "-fvara-fm-path="]

    @staticmethod
    def get_vara_tracing_cflags(
        instr_type: FeatureInstrType,
        save_temps: bool = False,
        project: tp.Optional[VProject] = None,
        instruction_threshold: tp.Optional[int] = None
    ) -> tp.List[str]:
        """
        Returns the cflags needed to trace projects with VaRA, using the
        specified tracer code.

        Args:
            instr_type: instrumentation type to use
            save_temps: saves temporary LLVM-IR files (good for debugging)
            project: project for which the cflags are used
            instruction_threshold: minimum function size to instrument

        Returns: list of tracing specific cflags
        """
        c_flags = []
        if instr_type != FeatureInstrType.NONE:
            c_flags += ["-fsanitize=vara", f"-fvara-instr={instr_type.value}"]
        c_flags += [
            "-flto", "-fuse-ld=lld", "-flegacy-pass-manager",
            "-fno-omit-frame-pointer"
        ]
        if instruction_threshold is not None:
            # For test projects, do not exclude small regions
            if project is not None and project.domain == ProjectDomains.TEST:
                instruction_threshold = 1

            c_flags += [f"-fvara-instruction-threshold={instruction_threshold}"]
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

    def __init__(
        self,
        project: VProject,
        experiment_handle: ExperimentHandle,
        report_file_ending: str = "json"
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle
        self.__report_file_ending = report_file_ending

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
                self.project, binary, get_current_config_id(self.project)
            )

            with local.cwd(local.path(self.project.builddir)):
                with ZippedReportFolder(result_filepath.full_path()) as tmp_dir:
                    for prj_command in workload_commands(
                        self.project, binary, [WorkloadCategory.EXAMPLE]
                    ):
                        local_tracefile_path = Path(
                            tmp_dir
                        ) / f"trace_{prj_command.command.label}" \
                            f".{self.__report_file_ending}"
                        with local.env(VARA_TRACE_FILE=local_tracefile_path):
                            pb_cmd = prj_command.command.as_plumbum(
                                project=self.project
                            )
                            print(
                                f"Running example {prj_command.command.label}"
                            )

                            extra_options = get_extra_config_options(
                                self.project
                            )
                            with cleanup(prj_command):
                                pb_cmd(
                                    *extra_options,
                                    retcode=binary.valid_exit_codes
                                )

        return StepResult.OK


class RunVaRATracedXRayWorkloads(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedXRayBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(self, project: VProject, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> StepResult:
        return self.run_traced_code()

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run VaRA measurements together with XRay",
            indent * " "
        )

    def run_traced_code(self) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        for binary in self.project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                # Skip libraries as we cannot run them
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
                        trace_result_path = Path(
                            tmp_dir
                        ) / f"trace_{prj_command.command.label}.json"
                        with local.env(
                            VARA_TRACE_FILE=trace_result_path,
                            XRAY_OPTIONS=" ".join([
                                "patch_premain=true",
                                "xray_mode=xray-basic",
                                "verbosity=1",
                            ]),
                        ):
                            pb_cmd = prj_command.command.as_plumbum(
                                project=self.project
                            )
                            print(
                                "Running example"
                                f" '{prj_command.command.label}'",
                                flush=True
                            )
                            with cleanup(prj_command):
                                _, _, err = pb_cmd.run()
                            xray = re.findall(
                                r"XRay: Log file in '(.+?)'",
                                err,
                                flags=re.DOTALL
                            )

                        if xray:
                            xray_log_path = local.cwd / xray[0]
                            xray_map_path = local.path(
                                self.project.primary_source
                            ) / binary.path
                            print(
                                f"XRay: Log file in '{xray_log_path}' /"
                                f" {xray_map_path}",
                                flush=True
                            )
                            xray_result_path = Path(
                                tmp_dir
                            ) / f"xray_{prj_command.command.label}.json"
                            local["llvm-xray"]([
                                "convert",
                                f"--instr_map={xray_map_path}",
                                f"--output={xray_result_path}",
                                "--output-format=trace_event",
                                "--symbolize",
                                xray_log_path,
                            ])

                            merge_result_path = Path(
                                tmp_dir
                            ) / f"merge_{prj_command.command.label}.json"

                            with open(
                                merge_result_path, mode="x", encoding="UTF-8"
                            ) as file:
                                file.write(
                                    json.dumps(
                                        merge_trace(
                                            (trace_result_path, "Trace"),
                                            (xray_result_path, "XRay")
                                        ),
                                        indent=2
                                    )
                                )

        return StepResult.OK

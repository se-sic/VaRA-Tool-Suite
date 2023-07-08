"""Module for feature performance precision experiments that evaluate
measurement support of vara."""
import shutil
import tempfile
import textwrap
import typing as tp
from pathlib import Path

import benchbuild.extensions as bb_ext
from benchbuild.command import cleanup
from benchbuild.utils import actions
from benchbuild.utils.actions import (
    ProjectStep,
    Step,
    StepResult,
    Compile,
    Clean,
)
from benchbuild.utils.cmd import time
from plumbum import local, ProcessExecutionError

from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    WithUnlimitedStackSize,
    ZippedReportFolder,
    create_new_success_result_filepath,
    get_current_config_id,
    get_default_compile_error_wrapped,
    get_extra_config_options,
    ZippedExperimentSteps,
)
from varats.experiment.workload_util import WorkloadCategory, workload_commands
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    RunVaRATracedXRayWorkloads,
    FeatureInstrType,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import ReportSpecification, ReportTy, BaseReport
from varats.report.tef_report import TEFReport, TEFReportAggregate
from varats.utils.git_commands import apply_patch


class MultiPatchReport(
    BaseReport, tp.Generic[ReportTy], shorthand="MPR", file_type=".zip"
):

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)
        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            # TODO: clean up
            for report in Path(tmp_result_dir).iterdir():
                if report.name.startswith("old"):
                    self.__old = report_type(report)
                elif report.name.startswith("new"):
                    self.__new = report_type(report)

            if not self.__old or not self.__new:
                raise AssertionError(
                    "Reports where missing in the file {report_path=}"
                )

    def get_old_report(self) -> ReportTy:
        return self.__old

    def get_new_report(self) -> ReportTy:
        return self.__new


class MPRTRA(
    MultiPatchReport[TimeReportAggregate], shorthand="MPRTRA", file_type=".zip"
):

    def __init__(self, path: Path) -> None:
        super().__init__(path, TimeReportAggregate)


class ReCompile(ProjectStep):
    NAME = "RECOMPILE"
    DESCRIPTION = "Recompile the project"

    def __call__(self, _: tp.Any) -> StepResult:
        try:
            self.project.recompile()

        except ProcessExecutionError:
            self.status = StepResult.ERROR
        self.status = StepResult.OK

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Recompile", indent * " "
        )


class ApplyPatch(ProjectStep):
    NAME = "APPLY_PATCH"
    DESCRIPTION = "Apply a patch the project"

    def __init__(self, project: VProject, patch_file: Path) -> None:
        super().__init__(project)
        self.__patch_file = patch_file

    def __call__(self, _: tp.Any) -> StepResult:
        try:
            print(
                f"Applying {self.__patch_file} to {self.project.source_of(self.project.primary_source)}"
            )
            apply_patch(
                Path(self.project.source_of(self.project.primary_source)),
                self.__patch_file
            )
        except ProcessExecutionError:
            self.status = StepResult.ERROR
        self.status = StepResult.OK

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Apply patch", indent * " "
        )


class RunTEFTracedWorkloads(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "json"
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__result_pre_fix = result_post_fix

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            for prj_command in workload_commands(
                self.project, self.__binary, [WorkloadCategory.EXAMPLE]
            ):
                local_tracefile_path = Path(tmp_dir) / (
                    f"{self.__result_pre_fix}_trace_"
                    f"{prj_command.command.label}_.{self.__report_file_ending}"
                )
                with local.env(VARA_TRACE_FILE=local_tracefile_path):
                    pb_cmd = prj_command.command.as_plumbum(
                        project=self.project
                    )
                    print(f"Running example {prj_command.command.label}")

                    extra_options = get_extra_config_options(self.project)
                    with cleanup(prj_command):
                        pb_cmd(
                            *extra_options,
                            retcode=self.__binary.valid_exit_codes
                        )

        return StepResult.OK


class TEFProfileRunner(FeatureExperiment, shorthand="TEFp"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfiler"

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
        instr_type = FeatureInstrType.TEF

        project.cflags += self.get_vara_feature_cflags(project)

        threshold = 0 if project.DOMAIN.value is ProjectDomains.TEST else 100
        project.cflags += self.get_vara_tracing_cflags(
            instr_type, project=project, instruction_threshold=threshold
        )

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        binary = project.binaries[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [  # type: ignore
                    RunTEFTracedWorkloads(
                        project, binary, result_post_fix="old"
                    ),
                    ApplyPatch(
                        project,
                        Path(
                            "/home/vulder/git/FeaturePerfCSCollection/test.patch"
                        )
                    ),
                    ReCompile(project),
                    RunTEFTracedWorkloads(
                        project, binary, result_post_fix="new"
                    )
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class RunBackBoxBaseline(ProjectStep):  # type: ignore
    """Executes the traced project binaries on the specified workloads."""

    NAME = "VaRARunTracedBinaries"
    DESCRIPTION = "Run traced binary on workloads."

    project: VProject

    def __init__(
        self,
        project: VProject,
        binary: ProjectBinaryWrapper,
        result_post_fix: str = "",
        report_file_ending: str = "txt",
        reps=2
    ):
        super().__init__(project=project)
        self.__binary = binary
        self.__report_file_ending = report_file_ending
        self.__result_pre_fix = result_post_fix
        self.__reps = reps

    def __call__(self, tmp_dir: Path) -> StepResult:
        return self.run_traced_code(tmp_dir)

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run instrumented code", indent * " "
        )

    def run_traced_code(self, tmp_dir: Path) -> StepResult:
        """Runs the binary with the embedded tracing code."""
        with local.cwd(local.path(self.project.builddir)):
            zip_tmp_dir = tmp_dir / f"{self.__result_pre_fix}_rep_measures"
            with ZippedReportFolder(zip_tmp_dir) as reps_tmp_dir:
                for rep in range(0, self.__reps):
                    for prj_command in workload_commands(
                        self.project, self.__binary, [WorkloadCategory.EXAMPLE]
                    ):
                        time_report_file = Path(reps_tmp_dir) / (
                            f"baseline_{prj_command.command.label}_{rep}_"
                            f".{self.__report_file_ending}"
                        )

                        pb_cmd = prj_command.command.as_plumbum(
                            project=self.project
                        )
                        print(f"Running example {prj_command.command.label}")

                        timed_pb_cmd = time["-v", "-o", time_report_file,
                                            pb_cmd]

                        extra_options = get_extra_config_options(self.project)
                        with cleanup(prj_command):
                            timed_pb_cmd(
                                *extra_options,
                                retcode=self.__binary.valid_exit_codes
                            )

        return StepResult.OK


class BlackBoxBaselineRunner(FeatureExperiment, shorthand="BBBase"):
    """Test runner for feature performance."""

    NAME = "GenBBBaseline"

    REPORT_SPEC = ReportSpecification(MPRTRA)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-flto", "-fuse-ld=lld", "-fno-omit-frame-pointer"]

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        binary = project.binaries[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [  # type: ignore
                    RunBackBoxBaseline(project, binary, result_post_fix="old"),
                    ApplyPatch(
                        project,
                        Path(
                            "/home/vulder/git/FeaturePerfCSCollection/test.patch"
                        )
                    ),
                    ReCompile(project),
                    RunBackBoxBaseline(project, binary, result_post_fix="new")
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

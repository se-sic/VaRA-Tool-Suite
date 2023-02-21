""""Coverage experiment."""

import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.llvm_coverage_report import CoverageReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    get_extra_config_options,
    get_current_config_id,
    ZippedExperimentSteps,
)
from varats.experiment.wllvm import RunWLLVM
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class GenerateCoverage(actions.ProjectStep):  # type: ignore
    """GenerateCoverage experiment."""

    NAME = "GenerateCoverage"
    DESCRIPTION = (
        "Runs the instrumented binary file in \
        order to obtain the coverage information."
    )

    project: VProject

    def __init__(
        self,
        project: Project,
        workload_cmds: tp.List[ProjectCommand],
        _experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.__workload_cmds = workload_cmds

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        """Runs project and export coverage."""
        with local.cwd(self.project.builddir):
            if not self.__workload_cmds:
                # No workload to execute.
                # Fail because we don't get any coverage data
                return actions.StepResult.ERROR
            for prj_command in self.__workload_cmds:
                pb_cmd = prj_command.command.as_plumbum(project=self.project)

                extra_args = get_extra_config_options(self.project)
                profdata_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.profdata"
                )
                json_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=f".{extra_args}.json"
                )

                profile_raw_name = f"{prj_command.path.name}.profraw"
                run_cmd = pb_cmd.with_env(LLVM_PROFILE_FILE=profile_raw_name)
                llvm_profdata = local["llvm-profdata"]
                llvm_cov = local["llvm-cov"]
                llvm_cov = llvm_cov[
                    "export", f"--instr-profile={profdata_name}",
                    f"--compilation-dir={self.project.builddir}", run_cmd.cmd]

                with cleanup(prj_command):
                    run_cmd(*extra_args)
                    llvm_profdata(
                        "merge", profile_raw_name, "-o", profdata_name
                    )
                    (llvm_cov > str(json_name))()

        return actions.StepResult.OK


# Please take care when changing this file, see docs experiments/just_compile
class GenerateCoverageExperiment(VersionExperiment, shorthand="GenCov"):
    """Generates empty report file."""

    NAME = "GenerateCoverage"

    REPORT_SPEC = ReportSpecification(CoverageReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Activate source-based code coverage:
        # https://clang.llvm.org/docs/SourceBasedCodeCoverage.html
        project.cflags += [
            "-fprofile-instr-generate", "-fcoverage-mapping",
            f"-fcoverage-compilation-dir={project.builddir}"
        ]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = (
            run.RuntimeExtension(project, self) << time.RunWithTime()
        )

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = (
            compiler.RunCompiler(project, self) << RunWLLVM() <<
            run.WithTimeout()
        )

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))

        # Only consider binaries with a workload
        for binary in project.binaries:
            workload_cmds = workload_commands(
                project, binary, [WorkloadCategory.EXAMPLE]
            )
            if not workload_cmds:
                continue
            result_filepath = create_new_success_result_filepath(
                self.get_handle(),
                self.get_handle().report_spec().main_report,
                project,
                binary,
                get_current_config_id(project),
            )

            analysis_actions.append(actions.Echo(result_filepath))
            analysis_actions.append(
                ZippedExperimentSteps(
                    result_filepath,
                    [
                        GenerateCoverage(
                            project, workload_cmds, self.get_handle()
                        )
                    ],
                )
            )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

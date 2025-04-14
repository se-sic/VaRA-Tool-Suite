import json
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import ProjectStep, StepResult, Step, Clean
from plumbum import local, ProcessExecutionError

from varats.data.reports.llvm_cov_report import LLVMCoverageReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
)
from varats.experiment.workload_util import workload_commands
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class BuildWithCoverage(ProjectStep):

    def __init__(self, project: Project, build_cmd: tp.Callable) -> None:
        super().__init__(project)
        self.build_cmd = build_cmd

    def __call__(self) -> StepResult:
        with local.env(
            CFLAGS="-fprofile-instr-generate -fcoverage-mapping",
            CXXFLAGS="-fprofile-instr-generate -fcoverage-mapping",
            LDFLAGS=
            "-fprofile-instr-generate -fcoverage-mapping -rtlib=compiler-rt",
        ):
            try:
                self.build_cmd()
            except ProcessExecutionError:
                return StepResult.ERROR

        return StepResult.OK


class CollectCoverage(ProjectStep):

    def __init__(
        self,
        project: Project,
        output_file: Path,
        run_cmd: tp.Callable,
        prefix: str = "coverages"
    ) -> None:
        super().__init__(project)
        self.output_path = output_file
        self.run_cmd = run_cmd
        self.prefix = prefix

    def __call__(self) -> StepResult:
        coverage_raw_files = self.project.builddir / f"{self.project.name}-{self.prefix}-%p.profraw"

        with local.env(LLVM_PROFILE_FILE=str(coverage_raw_files)):
            try:
                self.run_cmd()
            except ProcessExecutionError:
                return StepResult.ERROR

        coverage_raw_files = self.project.builddir / f"{self.project.name}-{self.prefix}-*.profraw"

        # Merge the coverage information
        profdata_cmd = local["llvm-profdata"]["merge", "-sparse",
                                              str(coverage_raw_files), "-o",
                                              str(self.output_path)]

        try:
            bb.watch(profdata_cmd())()
        except ProcessExecutionError:
            return StepResult.ERROR


class MergeCoverages(ProjectStep):

    def __init__(
        self, project: Project, profdata_file: Path, binary_path: Path,
        prefix: str, output_path: Path
    ) -> None:
        super().__init__(project)
        self.profdata_file = profdata_file
        self.binary_path = binary_path
        self.prefix = prefix
        self.output_path = output_path

    def __call__(self) -> StepResult:
        coverages_dir = self.project.builddir / self.prefix / "coverage_output"
        coverages_dir.mkdir(parents=True, exist_ok=True)

        llvm_cov = local["llvm-cov"]["show", f"{self.binary_path}",
                                     f"-instr-profile={self.profdata_file}"
                                     "-use-color=0",
                                     "-show-instantiations=false",
                                     f"-output-dir={coverages_dir}"]

        try:
            bb.watch(llvm_cov())()
        except ProcessExecutionError:
            return StepResult.ERROR

        coverage_data = {}
        for report_file in coverages_dir.glob("*.txt"):
            if report_file.stem == "index":
                continue

            with open(report_file) as coverage_file:
                file_coverages = []

                # The first two lines only contain metadata
                for _ in range(2):
                    next(coverage_file)

                # Third line contains the file name
                file_name = next(coverage_file).strip()
                file_name = Path(file_name).relative_to(self.project.builddir)

                # The rest of the lines contain the coverage information
                interval_start = None
                for line in coverage_file:
                    # Check if the line is empty or only contains whitespace
                    if not line.strip():
                        continue

                    lineno, count, _ = line.split('|', 2)

                    lineno = int(lineno.strip())

                    # Count is either only whitespace, 0 or a number which may be abbreviated with multiplier (k, M, G)
                    # We only care whether the count is 0 or not
                    if count.strip():
                        count = 0 if count.strip() == "0" else 1
                    else:
                        count = 0

                    if interval_start is None:
                        if count > 0:
                            interval_start = lineno
                    else:
                        if count > 0:
                            continue

                        file_coverages.append((interval_start, lineno))
                        interval_start = None

                # We may have an open interval at the end
                if interval_start is not None:
                    file_coverages.append((interval_start, lineno))

                coverage_data[file_name] = file_coverages

        # Write the coverage data to a json file
        with open(self.output_path, "w") as json_file:
            json.dump(coverage_data, json_file, indent=2)

        return StepResult.OK


class CollectBinaryCoverages(FeatureExperiment, shorthand="CBC"):
    """Collects coverage information for all binaries of a project."""
    project: VProject

    NAME = "CollectBinaryCoverages"
    DESCRIPTION = "Collects coverage information for all binaries of a project."
    REPORT_SPEC = ReportSpecification(LLVMCoverageReport)

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
                                    << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        analysis_actions = [
            BuildWithCoverage(project, project.compile),
        ]

        for binary in project.binaries:
            profdata_file = self.project.builddir / f"{self.project.name}-{binary.name}.profdata"

            # TODO: Different workloads?
            binary_run_cmd = workload_commands(project, binary,
                                               [])[0].command.as_plumbum(
                                                   project=project
                                               )

            analysis_actions.append(
                CollectCoverage(
                    project, profdata_file, binary_run_cmd, binary.name
                )
            )

            result_file = create_new_success_result_filepath(
                self.get_handle(), LLVMCoverageReport, self.project, binary,
                get_current_config_id(project)
            )

            analysis_actions.append(
                MergeCoverages(
                    project, profdata_file, binary.path, binary.name,
                    result_file.full_path().absolute()
                )
            )

        analysis_actions.append(Clean(project))

        return analysis_actions

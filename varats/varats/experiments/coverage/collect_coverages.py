import json
import re
import textwrap
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import ProjectStep, StepResult, Step, Clean
from plumbum import local, ProcessExecutionError

from varats.data.reports.llvm_cov_report import LLVMCoverageReport, CodeRegion
from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
)
from varats.experiment.workload_util import workload_commands
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class BuildWithCoverage(ProjectStep):
    """Builds the project with coverage information enabled."""

    def __init__(self, project: Project, build_cmd: tp.Callable) -> None:
        """
        Args:
            project (Project): The project to build.
            build_cmd (Callable): The command to build the project.
        """
        super().__init__(project)
        self.build_cmd = build_cmd

    def __call__(self) -> StepResult:
        with local.env(
            CFLAGS="-fprofile-instr-generate -fcoverage-mapping",
            CXXFLAGS="-fprofile-instr-generate -fcoverage-mapping",
            #CMAKE_BUILD_TYPE="Debug",
        ):
            try:
                self.build_cmd()
            except ProcessExecutionError:

                return StepResult.ERROR

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Run custom build command with coverage flags",
            indent * " "
        )


class CollectCoverage(ProjectStep):

    def __init__(
        self,
        project: Project,
        output_file: Path,
        run_cmd: tp.Union[tp.Callable, ProjectCommand],
        prefix: str = "coverages"
    ) -> None:
        """
        Args:
            project: Project to collect coverage for
            output_file: Path to create the merged profdata file
            run_cmd: Callable to be run
            prefix: prefix for temporary coverage files
        """
        super().__init__(project)
        self.output_path = output_file
        self.run_cmd = run_cmd
        self.prefix = prefix

    def __call__(self) -> StepResult:
        coverage_raw_files = self.project.builddir / self.prefix / f"{self.project.name}-%p.profraw"

        with local.env(LLVM_PROFILE_FILE=str(coverage_raw_files)):
            try:
                if isinstance(self.run_cmd, ProjectCommand):
                    bb.watch(
                        self.run_cmd.command.as_plumbum(project=self.project)
                    )()
                else:
                    self.run_cmd()
            except ProcessExecutionError as pe:
                return StepResult.ERROR

        coverage_raw_files = local.path(
            self.project.builddir, self.prefix
        ) // f"{self.project.name}-*.profraw"

        # Merge the coverage information
        profdata_cmd = local["llvm-profdata"]["merge", "-sparse",
                                              coverage_raw_files, "-o",
                                              str(self.output_path)]

        try:
            bb.watch(profdata_cmd)()
        except ProcessExecutionError:
            return StepResult.ERROR

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Collect Coverage Information", indent * " "
        )


class MergeCoverages(ProjectStep):

    def __init__(
        self, project: Project, profdata_file: Path, binary_path: Path,
        prefix: str, output_path: Path
    ) -> None:
        """
        Args:
            project: Project to merge coverages for
            profdata_file: Generated profdata file
            binary_path: Path to binary that created the profdata file
            prefix: Prefix for temporary coverage files
            output_path: Output path for resulting json file
        """
        super().__init__(project)
        self.profdata_file = profdata_file
        self.binary_path = binary_path
        self.prefix = prefix
        self.output_path = output_path

    def __aggregate_coverages(
        self, coverages_dir: Path
    ) -> tp.Dict[str, tp.List[CodeRegion]]:
        coverage_data = {}
        for report_file in coverages_dir.rglob("*.txt"):
            if report_file.stem == "index":
                continue

            with open(report_file) as coverage_file:
                file_coverages = []

                # The first two lines only contain metadata
                for _ in range(2):
                    next(coverage_file)

                # Third line contains the file name
                line = next(coverage_file).strip()

                file_name = Path(line).relative_to(self.project.builddir)
                file_name = Path(*file_name.parts[1:])

                # The rest of the lines contain the coverage information
                interval_start = None
                for line in coverage_file:
                    # Check if the line is empty or only contains whitespace
                    if not line.strip():
                        continue

                    lineno, counts, _ = line.split('|', 2)

                    lineno = int(lineno.strip())

                    # Count is either only whitespace, 0 or a number
                    # which may be abbreviated with multiplier (k, M, G)
                    # We only care whether the count is 0 or not
                    if counts.strip():
                        count = 0 if counts.strip() == "0" else 1
                    else:
                        count = 0

                    if interval_start is None:
                        if count > 0:
                            interval_start = lineno
                    else:
                        if count > 0:
                            continue

                        file_coverages.append(
                            CodeRegion(interval_start, lineno)
                        )
                        interval_start = None

                # We may have an open interval at the end
                if interval_start is not None:
                    file_coverages.append(CodeRegion(interval_start, lineno))

                coverage_data[str(file_name)] = file_coverages

        return coverage_data

    def __collect_linked_libraries(self, binary_path: Path) -> tp.List[Path]:
        """
        Use ldd to check which libraries are linked to the binary.

        Args:
            binary_path: Path to the binary to check.

        Returns:
            List of paths to the linked libraries that reside in the projects path.
        """
        ldd = local["ldd"][binary_path]

        try:
            out = ldd()
        except ProcessExecutionError:
            print(f"Error while executing ldd on {binary_path}")
            return []

        linked_libs = []

        for line in out.splitlines():
            path_candidate: str = line.split("=>", maxsplit=1)[-1]
            path_candidate = path_candidate[:path_candidate.rfind("(")].strip()

            lib_path = Path(path_candidate)
            if not lib_path.is_absolute():
                # Combine with path of the binary
                lib_path = binary_path.parent / lib_path

            if not lib_path.exists():
                # If the library is not found, skip it
                continue

            if lib_path.is_relative_to(self.project.builddir):
                linked_libs.append(lib_path)

        return linked_libs

    def __call__(self) -> StepResult:
        coverages_dir = Path(self.project.builddir) / self.prefix / "coverages"
        coverages_dir.mkdir(parents=True, exist_ok=True)

        linked_libs = self.__collect_linked_libraries(self.binary_path)

        cov_args = [
            "show", f"-instr-profile={self.profdata_file}", "-use-color=0",
            "-show-instantiations=false", f"-output-dir={coverages_dir}",
            f"-object={self.binary_path}"
        ]

        cov_args += [f"-object={lib}" for lib in linked_libs]

        llvm_cov = local["llvm-cov"][cov_args]

        try:
            bb.watch(llvm_cov)()
        except ProcessExecutionError:
            return StepResult.ERROR

        print(coverages_dir)

        coverage_data = self.__aggregate_coverages(coverages_dir)
        # Write the coverage data to a json file
        with open(self.output_path, "w") as json_file:
            json.dump(
                coverage_data, json_file, indent=2, default=CodeRegion.to_json
            )

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Merge Coverage Information", indent * " "
        )


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
            if binary.type != BinaryType.EXECUTABLE:
                continue

            profdata_file = project.builddir / f"{project.name}-{binary.name}.profdata"

            # TODO: Different workloads?
            workloads = workload_commands(project, binary, [])
            if not workloads:
                print(f"No workloads found for {binary.name}")
                continue

            binary_run_cmd = workloads[0]

            analysis_actions.append(
                actions.Echo(f"Collect coverage for {binary.name}")
            )
            analysis_actions.append(
                CollectCoverage(
                    project, profdata_file, binary_run_cmd, binary.name
                )
            )

            result_file = create_new_success_result_filepath(
                self.get_handle(), LLVMCoverageReport, project, binary,
                get_current_config_id(project)
            )

            analysis_actions.append(
                MergeCoverages(
                    project, profdata_file,
                    Path(project.source_of_primary) / binary.path, binary.name,
                    result_file.full_path().absolute()
                )
            )

        analysis_actions.append(Clean(project))

        return analysis_actions

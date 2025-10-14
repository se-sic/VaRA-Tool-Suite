"""
Experiments to collect coverages of different executables of a project.

Includes experiment steps for building the project with coverage information,
running the project and collecting the coverage information.
"""
import json
import textwrap
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.command import ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.project import Project
from benchbuild.utils import actions
from benchbuild.utils.actions import (
    ProjectStep,
    StepResult,
    Step,
    Clean,
    Compile,
)
from plumbum import local, ProcessExecutionError

from varats.data.reports.llvm_cov_report import (
    LLVMCoverageReport,
    CodeRegion,
    MWLCoverageReport,
)
from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
    AsOutputFolderStep,
)
from varats.experiment.steps.testsuite import PrepareTestSuite
from varats.experiment.workload_util import (
    workload_commands,
    create_workload_specific_filename,
)
from varats.experiments.vara.feature_experiment import FeatureExperiment
from varats.project.project_util import BinaryType, ProjectBinaryWrapper
from varats.project.varats_project import VProject, SupportsTestSuites
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id


class BuildWithCoverage(ProjectStep):  # type: ignore
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
            f"* {self.project.name}: "
            f"Run custom build command with coverage flags", indent * " "
        )


class CollectCoverage(ProjectStep):  # type: ignore
    """
    Collects coverage information for a project.

    Can operate either on project steps or generic callable functions. The
    callable should execute some code compiled with the necessary coverage
    flags.
    """

    def __init__(
        self,
        project: Project,
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
        self.run_cmd = run_cmd
        self.prefix = prefix

    def __call__(self) -> StepResult:
        with local.cwd(self.project.builddir):
            coverage_raw_files = (
                self.project.builddir / self.prefix /
                f"{self.project.name}-%p.profraw"
            )
            print(f"Current working dir: {local.cwd}")

            with local.env(LLVM_PROFILE_FILE=str(coverage_raw_files)):
                try:
                    if isinstance(self.run_cmd, ProjectCommand):
                        bb.watch(
                            self.run_cmd.command.as_plumbum(
                                project=self.project
                            )
                        )()
                    else:
                        self.run_cmd()
                except ProcessExecutionError:
                    return StepResult.ERROR

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Collect Coverage Information", indent * " "
        )


@AsOutputFolderStep("output_path")
class MergeCoverages(ProjectStep):  # type: ignore
    """Merges and aggregates coverage information from profdata files."""

    def __init__(
        self, project: Project, binary_paths: tp.Union[Path, tp.Iterable[Path]],
        prefixes: tp.Union[str, tp.Iterable[str]], output_prefix: str,
        output_path: Path
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
        if isinstance(binary_paths, Path):
            self.binary_paths = [binary_paths]
        else:
            self.binary_paths = list(binary_paths)

        if isinstance(prefixes, str):
            self.prefixes = [prefixes]
        else:
            self.prefixes = list(prefixes)
        self.output_path = output_path
        self.prefix = output_prefix

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
                line = next(coverage_file).strip().strip(":")

                file_name = Path(line).relative_to(self.project.builddir)
                file_name = Path(*file_name.parts[1:])

                # The rest of the lines contain the coverage information
                interval_start = None
                for line in coverage_file:
                    # Check if the line is empty or only contains whitespace
                    if not line.strip():
                        continue

                    l, counts, _ = line.split('|', 2)

                    lineno = int(l.strip())

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

    def __collect_linked_libraries(
        self, binary_paths: tp.List[Path]
    ) -> tp.List[Path]:
        """
        Use ldd to check which libraries are linked to the binary.

        Args:
            binary_path: Path to the binary to check.

        Returns:
            List of paths to the linked libraries that
            reside in the projects own source directory.
        """
        linked_libs = []
        for binary_path in binary_paths:
            ldd = local["ldd"][binary_path]

            try:
                out = ldd()
            except ProcessExecutionError:
                print(f"Error while executing ldd on {binary_path}")
                continue

            for line in out.splitlines():
                path_candidate: str = line.split("=>", maxsplit=1)[-1]
                path_candidate = path_candidate[:path_candidate.
                                                rfind("(")].strip()

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
        coverage_raw_files = [
            local.path(self.project.builddir, prefix) //
            f"{self.project.name}-*.profraw" for prefix in self.prefixes
        ]

        profdata_file = self.project.builddir / f"{self.prefix}.profdata"

        # Merge the coverage information
        profdata_cmd = local["llvm-profdata"]["merge", "-sparse",
                                              *coverage_raw_files, "-o",
                                              str(profdata_file)]

        try:
            bb.watch(profdata_cmd)()
        except ProcessExecutionError:
            return StepResult.ERROR

        coverages_dir = Path(self.project.builddir) / self.prefix / "coverages"
        coverages_dir.mkdir(parents=True, exist_ok=True)

        linked_libs = self.__collect_linked_libraries(self.binary_paths)

        cov_args = [
            "show", f"-instr-profile={profdata_file}", "-use-color=0",
            "-show-instantiations=false", f"-output-dir={coverages_dir}"
        ]

        cov_args += [f"-object={bin}" for bin in self.binary_paths]

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

        project.cflags.extend([
            "-fprofile-instr-generate", "-fcoverage-mapping"
        ])

        analysis_actions: tp.MutableSequence[Step] = [
            Compile(project),
        ]

        binaries = []
        prefixes = []

        for binary in project.binaries:
            if binary.type != BinaryType.EXECUTABLE:
                continue

            if project.name == "FastDownward" and binary.name == "FDDriverPy":
                # Skip python driver for FastDownward
                continue

            workloads = workload_commands(project, binary, [])
            if not workloads:
                print(f"No workloads found for {binary.name}")
                continue

            aggregated_result_file = create_new_success_result_filepath(
                self.get_handle(), MWLCoverageReport, project, binary,
                get_current_config_id(project)
            )

            zipped_steps = []

            for binary_run_cmd in workloads:
                zipped_steps.append(
                    actions.Echo(f"Collect coverage for {binary.name}")
                )
                zipped_steps.append(
                    CollectCoverage(project, binary_run_cmd, binary.name)
                )

                workload_result_file = create_workload_specific_filename(
                    binary.name, binary_run_cmd.command, file_suffix=".json"
                )

                binary_path = Path(
                    project.source_of_primary
                ) / binary_run_cmd.path
                workload_prefix = f"{binary.name}-{binary_run_cmd.command.label}"

                zipped_steps.append(
                    MergeCoverages(
                        project, binary_path, workload_prefix, workload_prefix,
                        workload_result_file
                    )
                )

                binaries.append(binary_path)
                prefixes.append(workload_prefix)

            if len(zipped_steps) == 0:
                continue

            analysis_actions.append(
                ZippedExperimentSteps(aggregated_result_file, zipped_steps)
            )

        if len(analysis_actions) == 1:
            # No workloads found for any binary
            return []

        # Final aggregation step for all binaries
        fake_binary = ProjectBinaryWrapper(
            "ALLBINARIES", Path(), BinaryType.EXECUTABLE
        )

        result_file = create_new_success_result_filepath(
            self.get_handle(), LLVMCoverageReport, project, fake_binary,
            get_current_config_id(project)
        )

        analysis_actions.append(
            MergeCoverages(
                project, binaries, prefixes, "ALLBINARIES",
                result_file.full_path().absolute()
            )
        )

        analysis_actions.append(Clean(project))

        return analysis_actions


class CollectTestCoverages(FeatureExperiment, shorthand="CTC"):
    """Collects coverage information for all binaries of a project."""
    project: VProject
    NAME = "CollectTestCoverages"
    DESCRIPTION = "Collects coverage information for all tests of a project."
    REPORT_SPEC = ReportSpecification(LLVMCoverageReport)

    def __init__(
        self, test_binary_map: tp.Callable[[VProject, str], tp.Optional[Path]]
    ) -> None:
        """
        Args:
            test_binary_map: Callable to get the path of the test binary
                             for a specific test case
        """
        super().__init__()
        self.test_binary_map = test_binary_map

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )
        if not isinstance(project, SupportsTestSuites):
            print(f"{project.name} does not support testing")
            return []

        project: tp.Union[VProject, SupportsTestSuites]

        analysis_actions: tp.List[Step] = [
            PrepareTestSuite(project),
            BuildWithCoverage(project, project.build_tests)
        ]

        test_names = project.get_test_names()

        coverage_steps = []

        for test_name in test_names:
            coverage_steps.append(
                actions.Echo(f"Collect coverage for test '{test_name}'")
            )

            profdata_file = (
                project.builddir /
                f"{project.name}-{test_name}-coverage.profdata"
            )

            def test_cmd():
                project.run_testsuite(
                    test_report_path=None, tests_to_run=[test_name]
                )

            coverage_steps.append(
                CollectCoverage(project, profdata_file, test_cmd, test_name)
            )

            test_binary = self.test_binary_map(project, test_name)

            if test_binary is None:
                print(f"No test binary found for {test_name}")
                continue

            fake_binary = ProjectBinaryWrapper(
                f"TEST#{test_name}", Path(), BinaryType.EXECUTABLE
            )

            report_file = create_new_success_result_filepath(
                self.get_handle(), LLVMCoverageReport, project, fake_binary,
                get_current_config_id(project)
            )

            coverage_steps.append(
                MergeCoverages(
                    project, profdata_file, test_binary, test_name,
                    Path(report_file.full_path())
                )
            )

        if len(coverage_steps) == 0:
            # No tests to instrument
            return []

        fake_binary = ProjectBinaryWrapper(
            f"TESTCOVERAGES", Path(), BinaryType.EXECUTABLE
        )

        report_file = create_new_success_result_filepath(
            self.get_handle(), LLVMCoverageReport, project, fake_binary,
            get_current_config_id(project)
        )

        analysis_actions.append(
            ZippedExperimentSteps(report_file, coverage_steps)
        )

        return analysis_actions

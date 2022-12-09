""""Coverage experiment."""
from __future__ import annotations

import json
import typing as tp
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from benchbuild import Project
from benchbuild.command import cleanup, ProjectCommand
from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from plumbum import local

from varats.data.reports.empty_report import EmptyReport
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    get_default_compile_error_wrapped,
    create_new_success_result_filepath,
    ZippedExperimentSteps,
)
from varats.experiment.wllvm import RunWLLVM
from varats.experiment.workload_util import (
    workload_commands,
    WorkloadCategory,
    create_workload_specific_filename,
)
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class CodeRegionKind(Enum):
    """Code region kinds."""
    CODE = 0
    EXPANSION = 1
    SKIPPED = 2
    GAP = 3
    BRANCH = 4


@dataclass
class CodeRegion:
    """Code region tree."""
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    count: int
    kind: CodeRegionKind
    function: str
    parent: tp.Optional[CodeRegion] = None
    childs: tp.List[CodeRegion] = field(default_factory=list)

    @classmethod
    def from_list(cls, region: tp.List[int], function: str) -> CodeRegion:
        """Instantiates a CodeRegion from a list."""
        if len(region) > 5:
            assert region[5:7] == [
                0, 0
            ]  # Not quite sure yet what the zeros stand for.
        return cls(
            start_line=region[0],
            start_column=region[1],
            end_line=region[2],
            end_column=region[3],
            count=region[4],
            kind=CodeRegionKind(region[7]),
            function=function,
        )

    def iter_breadth_first(self) -> tp.Iterator:
        """Yields childs breadth_first."""
        todo = deque([self])

        while todo:
            node = todo.popleft()
            childs = list(node.childs)
            todo.extend(childs)
            yield node

    def iter_postorder(self) -> tp.Iterator:
        """Yields childs in postorder."""
        for child in self.childs:
            for x in child.iter_postorder():
                yield x
        yield self

    def has_parent(self) -> bool:
        if self.parent is None:
            return False
        return True

    def is_covered(self) -> bool:
        return self.count != 0

    def is_subregion(self, other: CodeRegion) -> bool:
        """Tests if the 'other' region fits fully into self."""
        start_ok = False
        end_ok = False

        if self.start_line < other.start_line:
            start_ok = True
        elif self.start_line == other.start_line:
            start_ok = self.start_column < other.start_column

        if self.end_line > other.end_line:
            end_ok = True
        elif self.end_line == other.end_line:
            end_ok = self.end_column > other.end_column

        return start_ok and end_ok

    def insert(self, region: CodeRegion) -> None:
        """
        Inserts the given code region into the tree.

        The new regions must not exist yet and must not overlap
        """
        if not self.is_subregion(region):
            raise ValueError("The given region is not a subregion!")
        if region in self:
            raise ValueError("The given region exists already!")

        # Find the right child to append to
        # Should be the first code region where region is a subregion
        # when traversing the tree in postorder
        for node in self.iter_postorder():
            if node.is_subregion(region):
                if len(node.childs) > 0:
                    # node is not a leaf node
                    # check which childs should become childs of regions
                    childs_to_move = []
                    for child in node.childs:
                        if region.is_subregion(child):
                            childs_to_move.append(child)
                    region.childs.extend(childs_to_move)
                    region.childs.sort()
                    for child in childs_to_move:
                        child.parent = region
                        node.childs.remove(child)
                node.childs.append(region)
                node.childs.sort()
                region.parent = node
                assert region.count <= node.count
                break

    def diff(self, region: CodeRegion) -> None:
        """Builds the difference between self and region by subtracting all
        counts in region from self."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            assert x == y, "CodeRegions are not identical"
            x.count -= y.count

    # Compare regions only depending on their
    # start lines and columns + their type

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeRegion):
            return False
        return (
            self.start_line == other.start_line and
            self.start_column == other.start_column and
            self.end_line == other.end_line and
            self.end_column == other.end_column and self.kind == other.kind
        )

    def __lt__(self, other: CodeRegion) -> bool:
        if (
            self.start_line < other.start_line or
            self.start_line == other.start_line and
            self.start_column < other.start_column
        ):
            return True
        return False

    def __gt__(self, other: CodeRegion) -> bool:
        return not (self == other) and other < self

    def __le__(self, other: CodeRegion) -> bool:
        return self == other or other < self

    def __ge__(self, other: CodeRegion) -> bool:
        return self == other or other > self

    def __contains__(self, element: CodeRegion) -> bool:
        for child in self.iter_breadth_first():
            if child == element:
                return True
        return False


FunctionCodeRegionMapping = tp.NewType(
    "FunctionCodeRegionMapping", tp.Dict[str, CodeRegion]
)
FilenameFunctionMapping = tp.NewType(
    "FilenameFunctionMapping", tp.Dict[str, FunctionCodeRegionMapping]
)


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
        experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.__workload_cmds = workload_cmds
        self.__experiment_handle = experiment_handle

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
                print(f"{pb_cmd}")

                profdata_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report",
                    prj_command.command,
                    file_suffix=".profdata"
                )
                json_name = tmp_dir / create_workload_specific_filename(
                    "coverage_report", prj_command.command, file_suffix=".json"
                )

                profile_raw_name = f"{prj_command.path.name}.profraw"
                run_cmd = pb_cmd.with_env(LLVM_PROFILE_FILE=profile_raw_name)
                llvm_profdata = local["llvm-profdata"]
                llvm_cov = local["llvm-cov"]
                llvm_cov = llvm_cov["export", run_cmd.cmd,
                                    f"--instr-profile={profdata_name}"]

                with cleanup(prj_command):
                    run_cmd()  # run_cmd("--slow")
                    llvm_profdata(
                        "merge", profile_raw_name, "-o", profdata_name
                    )
                    (llvm_cov > str(json_name))()
                    filename_function_mapping = self._import_functions(
                        json_file=json_name,
                        filename_function_mapping=FilenameFunctionMapping({}),
                    )

        return actions.StepResult.OK

    def _import_functions(
        self, json_file: Path,
        filename_function_mapping: FilenameFunctionMapping
    ) -> FilenameFunctionMapping:
        with json_file.open() as file:
            j = json.load(file)
        # Compatibility check
        try:
            j_type = j["type"]
            j_version = j["version"].split(".")
            assert j_type == "llvm.coverage.json.export" and j_version[0] == "2"
        except Exception as err:
            raise NotImplementedError(
                "Cannot import functions. Json format unknown"
            ) from err

        data: tp.Dict[str, tp.Any] = j["data"][0]
        # files: tp.List = data["files"]
        functions: tp.List[tp.Any] = data["functions"]
        totals: tp.Dict[str, tp.Any] = data["totals"]

        function_region_mapping = FunctionCodeRegionMapping({})

        for function in functions:
            name: str = function["name"]
            # count: int = function["count"]
            # branches: list = function["branches"]
            filenames: tp.List[str] = function["filenames"]
            assert len(filenames) == 1
            filename: str = filenames[0]
            regions: tp.List[tp.List[int]] = function["regions"]

            function_region_mapping = self._import_code_regions(
                name, regions, function_region_mapping
            )

        filename_function_mapping[filename] = function_region_mapping

        # sanity checking
        total_functions_count: int = totals["functions"]["count"]
        total_regions_count: int = totals["regions"]["count"]
        total_regions_covered: int = totals["regions"]["covered"]
        total_regions_notcovered: int = totals["regions"]["notcovered"]

        counted_functions = 0
        counted_code_regions = 0
        covered_regions = 0
        notcovered_regions = 0

        assert function_region_mapping is not None
        for function in function_region_mapping:
            counted_functions += 1
            code_region = function_region_mapping[function]
            for region in code_region.iter_breadth_first():
                if region.kind == CodeRegionKind.CODE:
                    counted_code_regions += 1
                    if region.is_covered():
                        covered_regions += 1
                    else:
                        notcovered_regions += 1
        assert counted_functions == total_functions_count
        assert counted_code_regions == total_regions_count
        assert counted_code_regions != 0
        assert covered_regions == total_regions_covered
        assert notcovered_regions == total_regions_notcovered

        return filename_function_mapping

    def _import_code_regions(
        self,
        function: str,
        regions: tp.List[tp.List[int]],
        function_region_mapping: FunctionCodeRegionMapping,
    ) -> FunctionCodeRegionMapping:
        code_region: CodeRegion = CodeRegion.from_list(regions[0], function)
        for region in regions[1:]:
            to_insert = CodeRegion.from_list(region, function)
            code_region.insert(to_insert)

        function_region_mapping[function] = code_region
        return function_region_mapping


# Please take care when changing this file, see docs experiments/just_compile
class GenerateCoverageExperiment(VersionExperiment, shorthand="GenCov"):
    """Generates empty report file."""

    NAME = "GenerateCoverage"

    REPORT_SPEC = ReportSpecification(EmptyReport)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Activate source-based code coverage:
        # https://clang.llvm.org/docs/SourceBasedCodeCoverage.html
        project.cflags += ["-fprofile-instr-generate", "-fcoverage-mapping"]

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

        # Only consider binaries with a workload
        workload_cmds_list = []
        for binary in project.binaries:
            workload_cmds = workload_commands(
                project, binary, [WorkloadCategory.EXAMPLE]
            )
            if workload_cmds:
                workload_cmds_list.append(workload_cmds)
        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report,
            project,
            binary,
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(actions.Echo(result_filepath))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath,
                [
                    GenerateCoverage(project, workload_cmds, self.get_handle())
                    for workload_cmds in workload_cmds_list
                ],
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions
"""Implements an empty experiment that just compiles the project."""
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
    # Taken from https://github.com/xd009642/llvm-profparser/blob/eeb2f839ec2e3709526f047b86930a4a2e2a0739/src/coverage/mod.rs#L69
    Code = 0
    Expansion = 1
    Skipped = 2
    Gap = 3
    Branch = 4


@dataclass
class CodeRegion(object):
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    count: int
    kind: CodeRegionKind
    function: str
    parent: CodeRegion = None
    childs: list[CodeRegion] = field(default_factory=list)

    @classmethod
    def from_list(cls, region: list, function: str):
        if len(region) > 5:
            assert region[5:7] == [
                0, 0
            ]  # Not quite sure yet what the zeros stand for.
        return cls(*region[:5], CodeRegionKind(region[7]), function)

    def iter_breadth_first(self) -> tp.Iterator:
        todo = deque([self])

        while todo:
            node = todo.popleft()
            childs = [x for x in node.childs]
            todo.extend(childs)
            yield node

    def iter_postorder(self) -> tp.Iterator:
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

    def is_subregion(self, other) -> bool:
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

    def insert(self, region: CodeRegion):
        """
        Inserts the given code region into the tree.

        The new regions must not exist yet and must not overlap
        """
        if not self.is_subregion(region):
            raise ValueError("The given region is not a subregion!")
        if region in self:
            raise ValueError("The given region exists already!")

        # Find the right child to append to
        # Should be the first code region where region is a subregion when traversing the tree in postorder
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

    # Compare regions only depending on their start lines and columns

    def __eq__(self, other) -> bool:
        return self.start_line == other.start_line and self.start_column == other.start_column and self.end_line == other.end_line and self.end_column == other.end_column and self.kind == other.kind

    def __lt__(self, other) -> bool:
        if self.start_line < other.start_line:
            return True
        elif self.start_line == other.start_line and self.start_column < other.start_column:
            return True
        return False

    def __gt__(self, other) -> bool:
        return not (self == other) and other < self

    def __le__(self, other) -> bool:
        return self == other or other < self

    def __ge__(self, other) -> bool:
        return self == other or other > self

    def __contains__(self, element) -> bool:
        for child in self.iter_breadth_first():
            if child == element:
                return True
        return False


FunctionCodeRegionMapping = tp.NewType(
    "FunctionCodeRegionMapping", dict[str, CodeRegion]
)
FilenameFunctionMapping = tp.NewType(
    "FilenameFunctionMapping", dict[str, FunctionCodeRegionMapping]
)


class GenerateCoverage(actions.ProjectStep):  # type: ignore
    """."""

    NAME = "GenerateCoverage"
    DESCRIPTION = "Runs the instrumented binary file in order to obtain the coverage information."

    project: VProject

    def __init__(
        self, project: Project, workload_cmds: tp.List[ProjectCommand],
        experiment_handle: ExperimentHandle
    ):
        super().__init__(project=project)
        self.__workload_cmds = workload_cmds
        self.__experiment_handle = experiment_handle

    def __call__(self, tmp_dir: Path) -> actions.StepResult:
        return self.analyze(tmp_dir)

    def analyze(self, tmp_dir: Path) -> actions.StepResult:
        with local.cwd(self.project.builddir):
            if not self.__workload_cmds:
                # No workload to execute. Fail because we don't get any coverage data
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
                    self._import_functions(json_file=json_name)

        return actions.StepResult.OK

    def _import_functions(
        self,
        json_file: Path,
        filename_function_mapping:
        FilenameFunctionMapping = FilenameFunctionMapping({})
    ) -> FilenameFunctionMapping:
        with json_file.open() as f:
            j = json.load(f)
        # Compatibility check
        try:
            j_type = j["type"]
            j_version = j["version"].split(".")
            assert (
                j_type == "llvm.coverage.json.export" and j_version[0] == "2"
            )
        except Exception as e:
            print(e)
            raise NotImplementedError(
                "Cannot import code segments. Json format unknown"
            )

        data: dict = j["data"][0]
        #files: list = data["files"]
        functions: list = data["functions"]
        totals: dict = data["totals"]

        function_region_mapping = None

        for function in functions:
            name: str = function["name"]
            count: int = function["count"]
            #branches: list = function["branches"]
            filenames: list = function["filenames"]
            assert len(filenames) == 1
            filename: str = filenames[0]
            regions: list[list[int]] = function["regions"]

            if function_region_mapping is None:
                function_region_mapping = self._import_code_regions(
                    name, regions
                )
            else:
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

        for file in filename_function_mapping:
            for function in filename_function_mapping[file]:
                counted_functions += 1
                code_region = filename_function_mapping[file][function]
                for region in code_region.iter_breadth_first():
                    if region.kind == CodeRegionKind.Code:
                        counted_code_regions += 1
                        if region.is_covered():
                            covered_regions += 1
                        else:
                            notcovered_regions += 1
        assert counted_functions == total_functions_count
        assert counted_code_regions == total_regions_count and counted_code_regions != 0
        assert covered_regions == total_regions_covered
        assert notcovered_regions == total_regions_notcovered

        return filename_function_mapping

    def _import_code_regions(
        self,
        function: str,
        regions: list[list[int]],
        function_region_mapping:
        FunctionCodeRegionMapping = FunctionCodeRegionMapping({})
    ) -> FunctionCodeRegionMapping:
        code_region = None
        for region in regions:
            if code_region is None:
                code_region = CodeRegion.from_list(region, function)
            else:
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

        # Activate source-based code coverage: https://clang.llvm.org/docs/SourceBasedCodeCoverage.html
        project.cflags += ["-fprofile-instr-generate", "-fcoverage-mapping"]

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << RunWLLVM() \
            << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        # Only consider binaries with a workload
        workload_cmds_list = []
        for binary in project.binaries:
            if workload_cmds := workload_commands(
                project, binary, [WorkloadCategory.EXAMPLE]
            ):
                workload_cmds_list.append(workload_cmds)
        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary
        )

        analysis_actions = []
        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(actions.Echo(result_filepath))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    GenerateCoverage(project, workload_cmds, self.get_handle())
                    for workload_cmds in workload_cmds_list
                ]
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions

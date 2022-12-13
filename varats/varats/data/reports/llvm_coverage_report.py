"""Code region tree and coverage report."""

from __future__ import annotations

import json
import shutil
import typing as tp
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from varats.report.report import BaseReport


class CodeRegionKind(Enum):
    """Code region kinds."""
    CODE = 0
    EXPANSION = 1
    SKIPPED = 2
    GAP = 3
    BRANCH = 4


@dataclass
class Segment:
    line: int
    column: int


class RegionStart(Segment):
    pass


class RegionEnd(Segment):
    pass


@dataclass
class CodeRegion:
    """Code region tree."""
    start: RegionStart
    end: RegionEnd
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
            start=RegionStart(line=region[0], column=region[1]),
            end=RegionEnd(line=region[2], column=region[3]),
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

        if self.start.line < other.start.line:
            start_ok = True
        elif self.start.line == other.start.line:
            start_ok = self.start.column < other.start.column

        if self.end.line > other.end.line:
            end_ok = True
        elif self.end.line == other.end.line:
            end_ok = self.end.column > other.end.column

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
            self.start.line == other.start.line and
            self.start.column == other.start.column and
            self.end.line == other.end.line and
            self.end.column == other.end.column and self.kind == other.kind
        )

    def __lt__(self, other: CodeRegion) -> bool:
        if (
            self.start.line < other.start.line or
            self.start.line == other.start.line and
            self.start.column < other.start.column
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


class CoverageReport(BaseReport, shorthand="CovR", file_type="json"):
    """Parses llvm-cov export json files and displays them."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(path, tmpdir)

            def json_filter(x: Path) -> bool:
                return x.name.endswith(".json")

            filename_function_mapping = FilenameFunctionMapping({})
            for json_file in filter(json_filter, Path(tmpdir).iterdir()):
                filename_function_mapping = self._import_functions(
                    json_file,
                    filename_function_mapping,
                )

        print(filename_function_mapping)

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

        # sanity checking
        self.__region_import_sanity_check(totals, function_region_mapping)

        filename_function_mapping[filename] = function_region_mapping

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

    def __region_import_sanity_check(
        self, totals: tp.Dict[str, tp.Any],
        function_region_mapping: FunctionCodeRegionMapping
    ) -> None:
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

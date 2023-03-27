"""Code region tree and coverage report."""

from __future__ import annotations

import json
import shutil
import string
import typing as tp
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from plumbum import colors
from plumbum.colorlib.styles import Color

from varats.report.report import BaseReport


class CodeRegionKind(int, Enum):
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

    def iter_breadth_first(self) -> tp.Iterator[CodeRegion]:
        """Yields childs breadth_first."""
        todo = deque([self])

        while todo:
            node = todo.popleft()
            childs = list(node.childs)
            todo.extend(childs)
            yield node

    def iter_preorder(self) -> tp.Iterator[CodeRegion]:
        """Yields childs in preorder."""
        yield self
        for child in self.childs:
            for x in child.iter_preorder():
                yield x

    def iter_postorder(self) -> tp.Iterator[CodeRegion]:
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
        return self.count > 0

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
                # Actually this is possible,
                # e.g. a for loop can be executed
                # more often than its function.
                #assert region.count <= node.count
                break

    def merge(self, region: CodeRegion) -> None:
        """Merges region into self by adding all counts of region to the counts
        of self."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            assert x == y, "CodeRegions are not identical"
            x.count += y.count

    def diff(self, region: CodeRegion) -> None:
        """Builds the difference between self (base code) and region (new code)
        by comparing them."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            assert x == y, "CodeRegions are not identical"
            if x.is_covered() and y.is_covered(
            ) or not x.is_covered() and not y.is_covered():
                # No difference in coverage
                x.count = 0
            elif x.is_covered() and not y.is_covered():
                # Coverage decreased
                x.count = -1
            elif not x.is_covered() and y.is_covered():
                # Coverage increased
                x.count = 1
            else:
                raise NotImplemented("Should not be possible!")

    def is_identical(self, other: object) -> bool:
        """Is the code region equal and has the same coverage?"""
        if not isinstance(other, CodeRegion):
            return False
        if not (self == other and self.count == other.count):
            return False
        for code_region_a, code_region_b in zip(
            self.iter_breadth_first(), other.iter_breadth_first()
        ):
            if not (
                code_region_a == code_region_b and
                code_region_a.count == code_region_b.count
            ):
                return False
        return True

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


class FunctionCodeRegionMapping(tp.Dict[str, CodeRegion]):
    """Mapping from function names to CodeRegion objects."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FunctionCodeRegionMapping):
            return False
        for self_value, other_value in zip(self.values(), other.values()):
            if not self_value.is_identical(other_value):
                return False
        return True


FilenameFunctionMapping = tp.NewType(
    "FilenameFunctionMapping", tp.DefaultDict[str, FunctionCodeRegionMapping]
)


class CoverageReport(BaseReport, shorthand="CovR", file_type="json"):
    """Parses llvm-cov export json files and displays them."""

    @classmethod
    def from_json(cls, json_file: Path) -> CoverageReport:
        """CoverageReport from JSON file."""
        c_r = cls(json_file)
        c_r.filename_function_mapping = c_r._import_functions(
            json_file,
            c_r.filename_function_mapping,
        )
        return c_r

    @classmethod
    def from_report(cls, report_file: Path) -> CoverageReport:
        """CoverageReport from report file."""
        c_r = cls(report_file)
        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(report_file, tmpdir)

            def json_filter(x: Path) -> bool:
                return x.name.endswith(".json")

            for json_file in filter(json_filter, Path(tmpdir).iterdir()):
                c_r.filename_function_mapping = c_r._import_functions(
                    json_file,
                    c_r.filename_function_mapping,
                )
        return c_r

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.filename_function_mapping = FilenameFunctionMapping(
            defaultdict(lambda: FunctionCodeRegionMapping({}))
        )

    def merge(self, report: CoverageReport) -> None:
        """Merge report into self."""
        for filename_a, filename_b in zip(
            self.filename_function_mapping, report.filename_function_mapping
        ):
            assert Path(filename_a).name == Path(filename_b).name

            for function_a, function_b in zip(
                self.filename_function_mapping[filename_a],
                report.filename_function_mapping[filename_b]
            ):
                assert function_a == function_b
                code_region_a = self.filename_function_mapping[filename_a][
                    function_a]
                code_region_b = report.filename_function_mapping[filename_b][
                    function_b]
                assert code_region_a == code_region_b

                code_region_a.merge(code_region_b)

    def diff(self, report: CoverageReport) -> None:
        """Diff report from self."""
        for filename_a, filename_b in zip(
            self.filename_function_mapping, report.filename_function_mapping
        ):
            assert Path(filename_a).name == Path(filename_b).name

            for function_a, function_b in zip(
                self.filename_function_mapping[filename_a],
                report.filename_function_mapping[filename_b]
            ):
                assert function_a == function_b
                code_region_a = self.filename_function_mapping[filename_a][
                    function_a]
                code_region_b = report.filename_function_mapping[filename_b][
                    function_b]
                assert code_region_a == code_region_b

                code_region_a.diff(code_region_b)

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

        absolute_path = j["absolute_path"]
        data: tp.Dict[str, tp.Any] = j["data"][0]
        # files: tp.List = data["files"]
        functions: tp.List[tp.Any] = data["functions"]
        totals: tp.Dict[str, tp.Any] = data["totals"]

        for function in functions:
            name: str = function["name"]
            # count: int = function["count"]
            # branches: list = function["branches"]
            filenames: tp.List[str] = function["filenames"]
            assert len(filenames) == 1
            filename: str = str(Path(filenames[0]).relative_to(absolute_path))
            regions: tp.List[tp.List[int]] = function["regions"]

            filename_function_mapping[filename] = self._import_code_regions(
                name, regions, filename_function_mapping[filename]
            )

        # sanity checking
        self.__region_import_sanity_check(totals, filename_function_mapping)

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
        filename_function_mapping: FilenameFunctionMapping
    ) -> None:
        total_functions_count: int = totals["functions"]["count"]
        total_regions_count: int = totals["regions"]["count"]
        total_regions_covered: int = totals["regions"]["covered"]
        total_regions_notcovered: int = totals["regions"]["notcovered"]

        counted_functions = 0
        counted_code_regions = 0
        covered_regions = 0
        notcovered_regions = 0

        for filename in filename_function_mapping:
            function_region_mapping = filename_function_mapping[filename]
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CoverageReport):
            return False
        for filename_a, filename_b in zip(
            self.filename_function_mapping, other.filename_function_mapping
        ):
            if (Path(filename_a).name == Path(filename_b).name) and (
                self.filename_function_mapping[filename_a]
                == other.filename_function_mapping[filename_b]
            ):
                continue
            return False
        return True

    def to_json(self) -> str:
        """
        Exports the internal representation as json.

        Note this json format differs from the llvm-cov export json format!
        """

        class EnhancedJSONEncoder(json.JSONEncoder):
            """Custom JSON Encoder to handle converting CodeRegions to json."""

            def default(self, o: tp.Any) -> tp.Any:
                if isinstance(o, CodeRegion):
                    result = {}
                    for (key, value) in o.__dict__.items():
                        # Exclude parent to avoid endless loops
                        if key != "parent":
                            result[key] = self.encode(value)
                    return result
                if is_dataclass(o):
                    return asdict(o)
                return super().default(o)

        return json.dumps(
            self.filename_function_mapping, cls=EnhancedJSONEncoder
        )


SegmentBuffer = tp.DefaultDict[int, tp.List[tp.Tuple[tp.Optional[int], str]]]


def cov_show(
    report: CoverageReport,
    base_dir: Path,
) -> str:
    """
    Returns a the coverage in text form similar to llvm-cov show.

    NOTE: The colored representation differs a bit!
    """
    result = []
    for file in sorted(list(report.filename_function_mapping)):
        function_region_mapping = report.filename_function_mapping[file]
        path = Path(file)
        tmp_value = _cov_show_file(path, base_dir, function_region_mapping, [])
        if not tmp_value[-1].endswith("\n"):
            # Add newline if file does not end with one
            tmp_value.append("\n")
        result.append("".join(tmp_value))

    return "\n".join(result) + "\n"


def _cov_show_file(
    rel_path: Path, base_dir: Path,
    function_region_mapping: FunctionCodeRegionMapping, buffer: tp.List[str]
) -> tp.List[str]:

    lines: tp.Dict[int, str] = {}
    path = base_dir / rel_path
    with open(path) as file:
        line_number = 1
        for line in file.readlines():
            lines[line_number] = line
            line_number += 1

    buffer.append(_color_str(f"{rel_path}:\n", colors.cyan))
    # {linenumber: [(count, line_part_1), (other count, line_part_2)]}
    segments_dict: SegmentBuffer = defaultdict(list)
    for function in function_region_mapping:
        region = function_region_mapping[function]
        segments_dict = _cov_show_function(region, lines, segments_dict)

    # Print rest of file
    segments_dict = __cov_fill_buffer(
        end_line=len(lines),
        end_column=len(lines[len(lines)]) + 1,
        count=None,
        lines=lines,
        buffer=segments_dict
    )

    buffer.append(__segments_dict_to_str(segments_dict))
    return buffer


def __segments_dict_to_str(
    segments_dict: tp.DefaultDict[int, tp.List[tp.Tuple[tp.Optional[int], str]]]
) -> str:
    """Constructs a str from the given segments dictionary."""
    buffer = []
    for line_number, segments in segments_dict.items():
        if len(segments) > 1:
            # Workaround: Ignore counts for last segment with whitespaces
            # and single ';' that ends with "\n"
            segments[-1] = (None, segments[-1][1]
                           ) if segments[-1][1].endswith("\n") and (
                               str.isspace(segments[-1][1].replace(";", "", 1))
                           ) else segments[-1]
        #buffer.append(str(segments) + "\n")
        counts = [segment[0] for segment in segments]

        def filter_nones(a: tp.List[tp.Optional[int]]) -> tp.Iterator[int]:
            for item in a:
                if item is not None:
                    yield item

        non_none_counts = list(filter_nones(counts))
        count: tp.Union[int, str] = ""
        if len(non_none_counts) > 0:
            count = max(non_none_counts, key=abs)
        buffer.append(f"{line_number:>5}|{count:>7}|")

        texts = [segment[1] for segment in segments]
        colored_texts = []
        for x, y in zip(counts, texts):
            if x is None or x != 0:
                colored_texts.append(y)
            elif x == 0:
                y_stripped = y.lstrip(f"else){string.whitespace}")
                if not y_stripped.startswith("{") and len(y_stripped) != 0:
                    y_stripped = y
                before = y[:len(y) - len(y_stripped)]
                y_stripped = y_stripped.rstrip("\n")
                after = ""
                len_after = len(y) - len(before) - len(y_stripped)
                if len_after > 0:
                    after = y[-len_after:]
                colored_text = f"{before}{_color_str(y_stripped, colors.bg.red)}{after}"
                colored_texts.append(colored_text)
            else:
                raise NotImplementedError

        buffer.append("".join(colored_texts))
    return "".join(buffer)


def _cov_show_function(
    region: CodeRegion, lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    # Print lines before region.
    prev_line, prev_column = __get_previous_line_and_column(
        region.start.line, region.start.column, lines
    )
    buffer = __cov_fill_buffer(
        end_line=prev_line,
        end_column=prev_column,
        count=None,
        lines=lines,
        buffer=buffer
    )

    buffer = _cov_show_function_inner(region, lines, buffer)

    return buffer


def _cov_show_function_inner(
    region: CodeRegion, lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    # Print childs
    for child in region.childs:
        prev_line, prev_column = __get_previous_line_and_column(
            child.start.line, child.start.column, lines
        )
        next_line, next_column = __get_next_line_and_column(lines, buffer)
        if not (
            next_line > prev_line or
            next_line == prev_line and next_column >= prev_column
        ):
            # There is a gap until the next child begins that must be filled
            buffer = __cov_fill_buffer(
                end_line=prev_line,
                end_column=prev_column,
                count=region.count,
                lines=lines,
                buffer=buffer
            )
        if child.kind in (CodeRegionKind.CODE, CodeRegionKind.EXPANSION):
            buffer = _cov_show_function_inner(child, lines, buffer)
        elif child.kind == CodeRegionKind.GAP:
            #child.count = None  # type: ignore
            buffer = _cov_show_function_inner(child, lines, buffer)
        elif child.kind == CodeRegionKind.SKIPPED:
            child.count = None  # type: ignore
            buffer = _cov_show_function_inner(child, lines, buffer)
        else:
            raise NotImplementedError

    # Print remaining region
    buffer = __cov_fill_buffer(
        end_line=region.end.line,
        end_column=region.end.column,
        count=region.count,
        lines=lines,
        buffer=buffer
    )

    return buffer


def __cov_fill_buffer(
    end_line: int, end_column: int, count: tp.Optional[int],
    lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    start_line, start_column = __get_next_line_and_column(lines, buffer)

    assert start_line >= 1 and start_line <= len(lines)
    assert start_column >= 1 and start_column - 1 <= len(lines[start_line])
    assert end_line >= 1 and end_line <= len(lines) and end_line >= start_line
    assert end_column >= 1 and end_column - 1 <= len(lines[end_line])
    assert (end_column >= start_column if start_line == end_line else True)

    for line_number in range(start_line, end_line + 1):
        if line_number == start_line and line_number == end_line:
            text = lines[line_number][start_column - 1:end_column - 1]

        elif line_number == start_line:
            text = lines[line_number][start_column - 1:]

        elif line_number == end_line:
            text = lines[line_number][:end_column - 1]

        else:
            text = lines[line_number]

        buffer[line_number].append((count, text))

    return buffer


def __get_next_line_and_column(lines: tp.Dict[int, str],
                               buffer: SegmentBuffer) -> tp.Tuple[int, int]:
    """
    Outputs the next line + column that is not yet in the buffer.

    Max ist last line + last_column of lines.
    """
    last_line = len(buffer)

    if last_line == 0:
        # Empty buffer, start at first line, first column
        return 1, 1

    len_line = len(lines[last_line])
    last_column = sum(map(lambda x: len(x[1]), buffer[last_line]))

    if last_column >= len_line and last_line < len(lines):
        next_line = last_line + 1
        next_column = 1
    else:
        next_line = last_line
        next_column = min(last_column + 1, len_line)

    return next_line, next_column


def __get_previous_line_and_column(
    line: int, column: int, lines: tp.Dict[int, str]
) -> tp.Tuple[int, int]:
    assert line >= 2
    assert column >= 1
    if column - 1 == 0:
        return line - 1, len(lines[line - 1])
    return line, column - 1


def _color_str(a: str, color: Color) -> tp.Any:
    """Wraps the string inside the color characters."""
    return color | a

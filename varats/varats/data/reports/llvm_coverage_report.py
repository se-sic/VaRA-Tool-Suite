"""Code region tree and coverage report."""

from __future__ import annotations

import csv
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

CUTOFF_LENGTH = 80


class CodeRegionKind(int, Enum):
    """Code region kinds."""
    CODE = 0
    EXPANSION = 1
    SKIPPED = 2
    GAP = 3
    BRANCH = 4


@dataclass(frozen=True)
class FrozenLocation:
    line: int
    column: int


@dataclass
class Location:
    line: int
    column: int


class RegionStart(Location):
    pass


class RegionEnd(Location):
    pass


def _format_features(features: tp.List[str]) -> str:
    features_txt = "^".join(sorted(features))
    if "^" in features_txt:
        features_txt = f"({features_txt})"
    return features_txt


@dataclass
class CodeRegion:  # pylint: disable=too-many-instance-attributes
    """Code region tree."""
    start: RegionStart
    end: RegionEnd
    count: int
    kind: CodeRegionKind
    function: str
    parent: tp.Optional[CodeRegion] = None
    childs: tp.List[CodeRegion] = field(default_factory=list)
    coverage_features: tp.List[str] = field(default_factory=list)
    coverage_features_set: tp.Set[str] = field(default_factory=set)
    vara_instrs: tp.List[VaraInstr] = field(default_factory=list)

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

    def features_threshold(self, features: tp.List[str]) -> float:
        """Returns the proportion of this features in vara instrs."""
        with_feature = []
        wo_feature = []

        for instr in self.vara_instrs:
            if instr.has_features(features):
                with_feature.append(instr)
            else:
                wo_feature.append(instr)

        denominator = (len(with_feature) + len(wo_feature))
        if denominator == 0:
            return float("-inf")
        return len(with_feature) / denominator

    def vara_features(self) -> tp.Set[str]:
        """Returns all features from annotated vara instrs."""
        features = set()
        for instr in self.vara_instrs:
            features.update(instr.features)

        return features

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
                if node.childs:
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
                break

    def merge(self, region: CodeRegion) -> None:
        """Merges region into self by adding all counts of region to the counts
        of self."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            if x != y:
                raise AssertionError("CodeRegions are not identical")
            x.count += y.count

    def combine_features(self, region: CodeRegion) -> None:
        """Combines features of region with features of self."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            if x != y:
                raise AssertionError("CodeRegions are not identical")
            x.coverage_features.extend(y.coverage_features)
            x.coverage_features_set.update(y.coverage_features_set)

    def find_code_region(self, line: int,
                         column: int) -> tp.Optional[CodeRegion]:
        """
        Returns the smallest code region with the corresponding location.

        If not found, returns None
        """
        if not self.is_location_inside(line, column):
            # Early exit. Location is not inside root node
            return None

        for node in self.iter_postorder():
            if node.is_location_inside(line, column):
                # node with location found.
                return node
        return None

    def is_location_inside(self, line: int, column: int) -> bool:
        if self.start.line <= line <= self.end.line:
            # Location could be inside. Check cases.
            if self.start.line == line == self.end.line:
                # Location in same line
                return self.start.column <= column <= self.end.column
            elif self.start.line == line:
                # Location in start line
                return self.start.column <= column
            elif self.end.line == line:
                # Location in end line
                return column <= self.end.column
            # Location neither in start line not in end line
            return self.start.line < line < self.end.line
        return False

    def diff(
        self,
        region: CodeRegion,
        features: tp.Optional[tp.List[str]] = None
    ) -> None:
        """
        Builds the difference between self (base code) and region (new code) by
        comparing them.

        If features are given, annotate them.
        """
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            assert x == y, "CodeRegions are not identical"
            if x.is_covered() and y.is_covered(
            ) or not x.is_covered() and not y.is_covered():
                # No difference in coverage
                x.count = 0
            elif x.is_covered() and not y.is_covered():
                # Coverage decreased
                x.count = -1
                if features is not None:
                    x.coverage_features_set.update(features)
                    x.coverage_features.append(f"-{_format_features(features)}")
            elif not x.is_covered() and y.is_covered():
                # Coverage increased
                x.count = 1
                if features is not None:
                    x.coverage_features_set.update(features)
                    x.coverage_features.append(f"+{_format_features(features)}")

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


class FilenameFunctionMapping(tp.DefaultDict[str, FunctionCodeRegionMapping]):
    """Mapping from filenames to FunctionCodeRegions."""


class FeatureKind(Enum):
    FEATURE_VARIABLE = "FVar"
    FEATURE_REGION = "FReg"
    NORMAL_REGION = "Norm"


@dataclass
class VaraInstr:
    """Instr exported from VaRA."""
    kind: FeatureKind
    source_file: Path
    line: int
    column: int
    features: tp.List[str]
    instr_index: int
    instr: str

    def has_features(self, features: tp.List[str]) -> bool:
        for feature in features:
            if feature not in self.features:
                return False
        return True


class LocationInstrMapping(tp.DefaultDict[FrozenLocation, tp.List[VaraInstr]]):
    """Mapping from location to VaRAInstr."""


class FilenameLocationMapping(tp.DefaultDict[str, LocationInstrMapping]):
    """Mapping from filenames to Locations."""


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

            def csv_filter(y: Path) -> bool:
                return y.name.endswith(".csv") or y.name.endswith(".ptfdd")

            for csv_file in filter(csv_filter, Path(tmpdir).iterdir()):
                c_r._parse_instrs(csv_file)

        return c_r

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        self.filename_function_mapping = FilenameFunctionMapping(
            FunctionCodeRegionMapping
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

    def combine_features(self, report: CoverageReport) -> None:
        """Combine features of report with self."""
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

                code_region_a.combine_features(code_region_b)

    def diff(
        self,
        report: CoverageReport,
        features: tp.Optional[tp.List[str]] = None
    ) -> None:
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

                code_region_a.diff(code_region_b, features)

    def _parse_instrs(self, csv_file: Path) -> None:
        with csv_file.open() as file:
            reader = csv.DictReader(file, quotechar="'", delimiter=";")
            for row in reader:
                kind = FeatureKind(row["type"])
                source_file = row["source_file"]
                line = int(row["line"])
                column = int(row["column"])
                location = FrozenLocation(line, column)
                _features = row["features"].split(",")
                # Don't consider features belonging to conditions a feature.
                features = []
                for feature in _features:
                    if not feature.startswith("__CONDITION__:"):
                        # Translate vara feature name to command-line option name

                        features.append(feature)
                instr_index = int(row["instr_index"])
                instr = row["instr"]
                vara_instr = VaraInstr(
                    kind, Path(source_file), line, column, features,
                    instr_index, instr
                )
                if source_file in self.filename_function_mapping:
                    for _, code_region_tree in self.filename_function_mapping[
                        source_file].items():
                        feature_node = code_region_tree.find_code_region(
                            location.line, location.column
                        )
                        if feature_node is not None:
                            feature_node.vara_instrs.append(vara_instr)

    def _import_functions(
        self, json_file: Path,
        filename_function_mapping: FilenameFunctionMapping
    ) -> FilenameFunctionMapping:
        with json_file.open() as file:
            try:
                coverage_json = json.load(file)
            except json.JSONDecodeError as err:
                raise NotImplementedError(
                    "Cannot import functions. No valid JSON file provided."
                ) from err
        # Compatibility check
        try:
            coverage_type = coverage_json["type"]
            coverage_version = coverage_json["version"].split(".")
            if coverage_type != "llvm.coverage.json.export":
                raise AssertionError("Unknown JSON type.")
            if coverage_version[0] != "2":
                raise AssertionError("Unknown llvm-cov JSON version.")
        except (KeyError, AssertionError) as err:
            raise NotImplementedError(
                "Cannot import functions. JSON format unknown"
            ) from err

        absolute_path = coverage_json["absolute_path"]
        data: tp.Dict[str, tp.Any] = coverage_json["data"][0]
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

            filename_function_mapping[filename] = FunctionCodeRegionMapping(
                # Fix function order. Otherwise static functions come last.
                sorted(
                    self._import_code_regions(
                        name, regions, filename_function_mapping[filename]
                    ).items(),
                    key=lambda item: item[1]
                )
            )
        filename_function_mapping = FilenameFunctionMapping(
            FunctionCodeRegionMapping,
            sorted(filename_function_mapping.items())
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


Count = tp.Optional[int]
LinePart = str
CoverageFeatures = tp.Optional[tp.List[str]]
CoverageFeaturesSet = tp.Optional[tp.Set[str]]
VaraFeatures = tp.Optional[tp.Set[str]]
Segment = tp.Tuple[Count, LinePart, CoverageFeatures, CoverageFeaturesSet,
                   VaraFeatures]
Segments = tp.List[Segment]
SegmentBuffer = tp.DefaultDict[int, Segments]
FileSegmentBufferMapping = tp.Mapping[str, SegmentBuffer]


def cov_segments(
    report: CoverageReport,
    base_dir: Path,
) -> FileSegmentBufferMapping:
    """Returns the all segments for this report."""
    file_segments_mapping = {}
    for file in list(report.filename_function_mapping):
        function_region_mapping = report.filename_function_mapping[file]
        path = Path(file)
        file_segments_mapping[file] = _cov_segments_file(
            path, base_dir, function_region_mapping
        )

    return file_segments_mapping


def _cov_segments_file(
    rel_path: Path,
    base_dir: Path,
    function_region_mapping: FunctionCodeRegionMapping,
) -> SegmentBuffer:

    lines: tp.Dict[int, str] = {}
    path = base_dir / rel_path
    with open(path) as file:
        line_number = 1
        for line in file.readlines():
            lines[line_number] = line
            line_number += 1

    # {linenumber: [(count, line_part_1), (other count, line_part_2)]}
    segments_dict: SegmentBuffer = defaultdict(list)
    for function in function_region_mapping:
        region = function_region_mapping[function]
        segments_dict = _cov_segments_function(region, lines, segments_dict)

    # Add rest of file
    segments_dict = __cov_fill_buffer(
        end_line=len(lines),
        end_column=len(lines[len(lines)]) + 1,
        count=None,
        cov_features=None,
        cov_features_set=None,
        vara_features=None,
        lines=lines,
        buffer=segments_dict
    )

    return segments_dict


def cov_show(
    report: CoverageReport,
    base_dir: Path,
) -> str:
    """
    Returns the coverage in text form similar to llvm-cov show.

    NOTE: The colored representation differs a bit!
    """
    return cov_show_segment_buffer(cov_segments(report, base_dir))


def cov_show_segment_buffer(
    file_segments_mapping: FileSegmentBufferMapping,
    show_counts: bool = True,
    show_coverage_features: bool = False,
    show_coverage_feature_set: bool = False,
    show_vara_features: bool = False,
) -> str:
    """Returns the coverage in text form."""
    result = []
    for file in file_segments_mapping:
        tmp_value = [_color_str(f"{file}:\n", colors.cyan)]
        tmp_value.append(
            __table_to_text(
                __segments_dict_to_table(
                    file_segments_mapping[file], color_counts=show_counts
                ),
                show_counts,
                show_coverage_features,
                show_coverage_feature_set,
                show_vara_features,
            )
        )

        if not tmp_value[-1].endswith("\n"):
            # Add newline if file does not end with one
            tmp_value.append("\n")

        result.append("".join(tmp_value))

    return "\n".join(result) + "\n"


class TableEntry(tp.NamedTuple):
    """Entry for __table_to_text."""
    count: tp.Union[int, str]  # type: ignore[assignment]
    text: str
    coverage_features: str
    coverage_feature_set: str
    vara_features: str


def __table_to_text(
    table: tp.Dict[int, TableEntry],
    show_counts: bool = True,
    show_coverage_features: bool = False,
    show_coverage_feature_set: bool = False,
    show_vara_features: bool = False,
) -> str:
    output = []
    for line_number, entry in table.items():
        line = []
        line.append(f"{line_number:>5}")
        if show_counts:
            line.append(f"|{entry.count:>7}")

        text = entry.text.replace("\n", "", 1)
        if not any([
            show_coverage_features, show_coverage_feature_set,
            show_vara_features
        ]):
            line.append(f"|{text}")
        else:
            text = text[:CUTOFF_LENGTH]
            line.append(f"|{text:<{CUTOFF_LENGTH}}")
        if show_coverage_features:
            line.append(f"|{entry.coverage_features}")
        if show_coverage_feature_set:
            line.append(f"|{entry.coverage_feature_set}")
        if show_vara_features:
            line.append(f"|{entry.vara_features}")
        output.append("".join(line))
    return "\n".join(output)


def __segments_dict_to_table( # pylint: disable=too-many-locals
    segments_dict: SegmentBuffer,
    color_counts: bool = False,
) -> tp.Dict[int, TableEntry]:
    """Constructs a str from the given segments dictionary."""
    table = {}
    for line_number, segments in segments_dict.items():
        if len(segments) > 1:
            # Workaround: Ignore counts for last segment with whitespaces
            # and single ';' that ends with "\n"
            segments[-1] = (None, segments[-1][1], None, None, None
                           ) if segments[-1][1].endswith("\n") and (
                               str.isspace(segments[-1][1].replace(";", "", 1))
                           ) else segments[-1]
        counts = [segment[0] for segment in segments]

        def filter_out_nones(a: tp.Iterable[tp.Any]) -> tp.Iterator[tp.Any]:
            for item in a:
                if item is not None:
                    yield item

        non_none_counts = list(filter_out_nones(counts))
        count: tp.Union[int, str] = ""
        if len(non_none_counts) > 0:
            count = max(non_none_counts, key=abs)

        texts = [segment[1] for segment in segments]
        colored_texts = []
        for x, y in zip(counts, texts):
            if not color_counts or x is None or x != 0:
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
                middle = _color_str(y_stripped, colors.bg.red)
                colored_text = f"{before}{middle}{after}"
                colored_texts.append(colored_text)
            else:
                raise NotImplementedError

        coverage_features = filter_out_nones(segment[2] for segment in segments)
        coverage_features_set = filter_out_nones(
            segment[3] for segment in segments
        )
        vara_features = filter_out_nones(segment[4] for segment in segments)

        table[line_number] = TableEntry(
            count,
            "".join(colored_texts),
            __feature_text(coverage_features),
            __feature_text(coverage_features_set),
            __feature_text(vara_features),
        )

    return table


def __feature_text(iterable: tp.Iterable[tp.Iterable[str]]) -> str:
    feature_buffer = set()
    for x in iterable:
        for feature in x:
            if feature.startswith("+"):
                feature_buffer.add(_color_str(feature, colors.green))
            elif feature.startswith("-"):
                feature_buffer.add(_color_str(feature, colors.red))
            else:
                feature_buffer.add(feature)
    return ', '.join(sorted(feature_buffer))


def _cov_segments_function(
    region: CodeRegion, lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    # Add lines before region.
    prev_line, prev_column = __get_previous_line_and_column(
        region.start.line, region.start.column, lines
    )
    buffer = __cov_fill_buffer(
        end_line=prev_line,
        end_column=prev_column,
        count=None,
        cov_features=None,
        cov_features_set=None,
        vara_features=None,
        lines=lines,
        buffer=buffer
    )

    buffer = _cov_segments_function_inner(region, lines, buffer)

    return buffer


def _cov_segments_function_inner(
    region: CodeRegion, lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    # Add childs
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
                cov_features=region.coverage_features,
                cov_features_set=region.coverage_features_set,
                vara_features=region.vara_features(),
                lines=lines,
                buffer=buffer
            )
        if child.kind in (CodeRegionKind.CODE, CodeRegionKind.EXPANSION):
            buffer = _cov_segments_function_inner(child, lines, buffer)
        elif child.kind == CodeRegionKind.GAP:
            #child.count = None  # type: ignore
            buffer = _cov_segments_function_inner(child, lines, buffer)
        elif child.kind == CodeRegionKind.SKIPPED:
            child.count = None  # type: ignore
            buffer = _cov_segments_function_inner(child, lines, buffer)
        else:
            raise NotImplementedError

    # Add remaining region
    buffer = __cov_fill_buffer(
        end_line=region.end.line,
        end_column=region.end.column,
        count=region.count,
        cov_features=region.coverage_features,
        cov_features_set=region.coverage_features_set,
        vara_features=region.vara_features(),
        lines=lines,
        buffer=buffer
    )

    return buffer


def __cov_fill_buffer(
    end_line: int, end_column: int, count: Count,
    cov_features: CoverageFeatures, cov_features_set: CoverageFeaturesSet,
    vara_features: VaraFeatures, lines: tp.Dict[int, str], buffer: SegmentBuffer
) -> SegmentBuffer:

    start_line, start_column = __get_next_line_and_column(lines, buffer)

    assert 1 <= start_line <= len(lines)
    assert start_column >= 1 and start_column - 1 <= len(lines[start_line])
    assert 1 <= end_line <= len(lines) and end_line >= start_line
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

        buffer[line_number].append(
            (count, text, cov_features, cov_features_set, vara_features)
        )

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

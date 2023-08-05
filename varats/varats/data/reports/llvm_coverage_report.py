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

from plumbum import colors, local
from plumbum.colorlib.styles import Color
from pyeda.boolalg.expr import Complement, Variable  # type: ignore
from pyeda.inter import (  # type: ignore
    Expression,
    exprvar,
    expr,
    espresso_exprs,
)

from varats.base.configuration import Configuration
from varats.report.report import BaseReport

TAB_SIZE = 8
CUTOFF_LENGTH = 80


class CodeRegionKind(int, Enum):
    """Code region kinds."""
    CODE = 0
    EXPANSION = 1
    SKIPPED = 2
    GAP = 3
    BRANCH = 4
    FILE_ROOT = -1


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


class PresenceKind(Enum):
    """Code region kinds."""
    BECOMES_ACTIVE = "+"
    BECOMES_INACTIVE = "-"


@dataclass
class PresenceCondition:
    """
    Presence Condition.

    Tells how the presence changed for this specific configuration.
    """
    kind: PresenceKind
    configuration: Configuration

    def __str__(self) -> str:
        return f"{self.kind.value}({self.configuration})"


def simplify(conditions: tp.List[PresenceCondition]) -> Expression:
    """Build the DNF of all conditions and simplify it."""
    dnf = expr(False)
    if not conditions:
        return dnf
    for condition in conditions:
        expression = expr(True)
        for option in condition.configuration.options():
            expr_var = exprvar(option.name)
            if bool(option.value):
                expression = expression & expr_var
            else:
                expression = expression & ~expr_var
        dnf = dnf | expression
    if dnf.equivalent(expr(True)):
        return expr(True)
    return espresso_exprs(dnf.to_dnf())[0]


class PresenceConditions(
    tp.DefaultDict[PresenceKind, tp.List[PresenceCondition]]
):
    """Presence Conditions obtained from diffing coverage data."""

    def extend(self, other: PresenceConditions) -> None:
        for kind, conditions in other.items():
            self[kind].extend(conditions)

    def simplify(self, kind: tp.Optional[PresenceKind] = None) -> Expression:
        """Build the DNF of all conditions for kind and simplifies it."""
        if kind is None:
            conditions = []
            for values in self.values():
                conditions.extend(values)
        else:
            conditions = self[kind]
        return simplify(conditions)

    def all_conditions(self) -> tp.Set[str]:
        """All conditions that are relevant."""
        output: tp.Set[str] = set()
        for presence_kind in self:
            if self[presence_kind]:
                output.update(
                    str(feature)
                    for feature in self.simplify(presence_kind).support
                )
        return output

    def __str__(self) -> str:
        output = []
        for presence_kind in self:
            if self[presence_kind]:
                expression = self.simplify(presence_kind)
                output.append(f"{presence_kind.value}{expr_to_str(expression)}")
        return ",".join(output)


def expr_to_str(expression: Expression) -> str:
    """Converts expression back to str representation."""
    if expression.is_zero() or expression.is_one():
        return str(bool(expression))
    if expression.ASTOP == "lit":
        if isinstance(expression, Complement):
            return f"~{expr_to_str(~expression)}"
        if isinstance(expression, Variable):
            return str(expression)
        raise NotImplementedError()
    if expression.ASTOP == "and":
        return f"({' & '.join(sorted(map(expr_to_str, expression.xs)))})"
    if expression.ASTOP == "or":
        return f"({' | '.join(sorted(map(expr_to_str, expression.xs)))})"
    raise NotImplementedError()


@dataclass
class CodeRegion:  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Code region tree."""
    start: RegionStart
    end: RegionEnd
    count: int
    kind: CodeRegionKind
    function: str
    filename: str
    #    expanded_from: tp.Optional[CodeRegion] = None
    parent: tp.Optional[CodeRegion] = None
    childs: tp.List[CodeRegion] = field(default_factory=list)
    presence_conditions: PresenceConditions = field(
        default_factory=lambda: PresenceConditions(list)
    )
    vara_instrs: tp.List[VaraInstr] = field(default_factory=list)
    counts: tp.List[int] = field(default_factory=list)
    instantiations: tp.List[str] = field(default_factory=list)

    @classmethod
    def from_list(
        cls, region: tp.List[int], function: str, filenames: tp.List[str]
    ) -> CodeRegion:
        """Instantiates a CodeRegion from a list."""

        # expansion_id = region[6]

        return cls(
            start=RegionStart(line=region[0], column=region[1]),
            end=RegionEnd(line=region[2], column=region[3]),
            count=region[4],
            kind=CodeRegionKind(region[7]),
            function=function,
            filename=filenames[region[5]]
        )

    @classmethod
    def from_file(cls, path: str) -> CodeRegion:
        """Instantiates a root code region from a file."""

        start = RegionStart(1, 1)
        # how long is the file?
        with open(path) as source_code:
            content = source_code.readlines()
        end_line = len(content)
        end_column = len(content[-1])
        end = RegionEnd(end_line, end_column)

        return cls(
            start=start,
            end=end,
            count=0,
            kind=CodeRegionKind.FILE_ROOT,
            function="__no_function_I_AM_ROOT__",
            filename=path
        )

    def __post_init__(self) -> None:
        self.counts.append(self.count)
        self.instantiations.append(self.function)
        # Ignore location in function_name (static function)
        self.function = self.function.split(":", 1)[-1]

    @property
    def total_count(self) -> int:
        return sum(self.counts)

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

    def features_threshold(self, features: tp.Iterable[str]) -> float:
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

    def coverage_features(self) -> str:
        """Returns presence conditions."""
        return str(self.presence_conditions)

    def coverage_features_set(self) -> tp.Set[str]:
        """Returns features affecting code region somehow."""
        return self.presence_conditions.all_conditions()

    def vara_features(self) -> tp.Set[str]:
        """Returns all features from annotated vara instrs."""
        features = set()
        for instr in self.vara_instrs:
            features.update(instr.features)

        return features

    def is_covered(self) -> bool:
        return self.total_count > 0

    def is_subregion(self, other: CodeRegion) -> bool:
        """
        Tests if the 'other' region fits fully into self.

        It fits if start equals but end is smaller or start is greater and end
        equal
        """
        start_ok = False
        end_ok = False
        start_equal = False
        end_equal = True

        if self.start.line < other.start.line:
            start_ok = True
        elif self.start.line == other.start.line:
            start_ok = self.start.column <= other.start.column
            start_equal = self.start.column == other.start.column

        if self.end.line > other.end.line:
            end_ok = True
        elif self.end.line == other.end.line:
            end_ok = self.end.column >= other.end.column
            end_equal = self.end.column == other.end.column

        return start_ok and end_ok and not (start_equal and end_equal)

    def overlaps(self, other: CodeRegion) -> bool:
        """
        Tests if regions overlap.

        They overlaps if they are not subregions, but one location is inside of
        the other.
        """

        if self.is_subregion(other) or other.is_subregion(self):
            return False
        if self.is_location_inside(
            other.start.line, other.start.column
        ) != other.is_location_inside(self.start.line, self.start.column):
            return True

        return False

    def add_instantiation(self, region: CodeRegion) -> None:
        """If a code region already exists in a tree."""
        if region != self:
            raise ValueError("The given region is identical!")

        self.counts.append(region.count)
        self.instantiations.append(region.function)

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

                if any(child.overlaps(region) for child in node.childs):
                    raise ValueError(
                        "The given region overlaps with another region!"
                    )
                node.childs.append(region)
                node.childs.sort()
                region.parent = node
                break

    def combine_features(self, region: CodeRegion) -> None:
        """Combines features of region with features of self."""
        for x, y in zip(self.iter_breadth_first(), region.iter_breadth_first()):
            if x != y:
                raise AssertionError("CodeRegions are not identical")
            x.presence_conditions.extend(y.presence_conditions)

    def get_code_region(self, element: CodeRegion) -> tp.Optional[CodeRegion]:
        """Returns the code region if it exists already."""
        for child in self.iter_breadth_first():
            if child == element:
                return child
        return None

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
        """Returns true if line and column is inside code region."""
        if self.start.line <= line <= self.end.line:
            # Location could be inside. Check cases.
            if self.start.line == line == self.end.line:
                # Location in same line
                return self.start.column <= column < self.end.column
            if self.start.line == line:
                # Location in start line
                return self.start.column <= column
            if self.end.line == line:
                # Location in end line
                return column < self.end.column
            # Location neither in start line not in end line
            return self.start.line < line < self.end.line
        return False

    def annotate_covered(self, configuration: Configuration) -> None:
        """
        Adds the presence condition to all covered regions.

        Ignore GAP regions without VaRA instructions.
        """
        kind = PresenceKind.BECOMES_ACTIVE
        for region in self.iter_breadth_first():
            if region.kind == CodeRegionKind.GAP:
                assert len(region.vara_instrs) == 0
                continue
            if region.is_covered():
                region.presence_conditions[kind].append(
                    PresenceCondition(kind, configuration)
                )

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

    # Compare regions only depending on their file,
    # start lines and columns + their type

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeRegion):
            return False

        return (
            self.start.line == other.start.line and
            self.start.column == other.start.column and
            self.end.line == other.end.line and
            self.end.column == other.end.column and self.kind == other.kind and
            self.filename == other.filename
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


class FilenameRegionMapping(tp.Dict[str, CodeRegion]):
    """Mapping from function names to CodeRegion objects."""

    def __init__(
        self,
        *args: tp.List[tp.Any],
        base_dir: tp.Optional[Path] = None,
        **kwargs: tp.Dict[str, tp.Any]
    ):
        self.base_dir = base_dir
        super().__init__(*args, **kwargs)

    def add(self, region: CodeRegion) -> None:
        """Adds a code region."""
        filename = region.filename
        if self.base_dir:
            file_path = self.base_dir / filename
        if filename not in self:
            if file_path.is_file():
                self[filename] = CodeRegion.from_file(str(file_path))
            else:
                print(
                    f"WARNING: '{filename}' is not a file. \
Ignoring region: {region}"
                )
                return
        root_region = self[filename]
        if (found_region := root_region.get_code_region(region)) is not None:
            # Region exists already
            found_region.add_instantiation(region)
        else:
            # Region does not exist
            root_region.insert(region)

    def sorted(self) -> FilenameRegionMapping:
        return FilenameRegionMapping(
            # Fix function order. Otherwise static functions come last.
            sorted(self.items())
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FilenameRegionMapping):
            return False

        for self_value, other_value in zip(self.values(), other.values()):
            if not self_value.is_identical(other_value):
                return False

        return True


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

    def has_features(self, features: tp.Iterable[str]) -> bool:
        """Checks if instr is marked with given features."""
        for feature in features:
            if feature not in self.features:
                return False
        return True


class CoverageReport(BaseReport, shorthand="CovR", file_type="json"):
    """Parses llvm-cov export json files and displays them."""

    @classmethod
    def from_json(cls, json_file: Path, base_dir: Path) -> CoverageReport:
        """CoverageReport from JSON file."""
        c_r = cls(json_file, base_dir=base_dir)
        c_r.tree = c_r._import_functions(json_file, c_r.tree)
        return c_r

    @classmethod
    def from_report(
        cls, report_file: Path, configuration: Configuration, base_dir: Path
    ) -> CoverageReport:
        """CoverageReport from report file."""
        c_r = cls(report_file, configuration, base_dir)
        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(report_file, tmpdir)

            def xml_filter(y: Path) -> bool:
                return y.name.endswith(".xml")

            xmls = list(filter(xml_filter, Path(tmpdir).iterdir()))
            assert len(xmls) == 1
            for xml_file in xmls:
                c_r._extract_feature_option_mapping(xml_file)

            def json_filter(x: Path) -> bool:
                return x.name.endswith(".json")

            jsons = list(filter(json_filter, Path(tmpdir).iterdir()))
            for json_file in jsons:
                c_r.tree = c_r._import_functions(json_file, c_r.tree)

            def csv_filter(y: Path) -> bool:
                return y.name.endswith(".csv") or y.name.endswith(".ptfdd")

            csvs = list(filter(csv_filter, Path(tmpdir).iterdir()))
            assert len(csvs) == 1
            for csv_file in csvs:
                c_r._parse_instrs(csv_file)

            if c_r.configuration is not None:
                c_r.annotate_covered(c_r.configuration)

        return c_r

    def __init__(
        self,
        path: Path,
        configuration: tp.Optional[Configuration] = None,
        base_dir: tp.Optional[Path] = None
    ) -> None:
        super().__init__(path)

        self.tree = FilenameRegionMapping(base_dir=base_dir)
        self.absolute_path = ""
        self.featue_option_mapping: tp.Dict[str, tp.Union[str,
                                                          tp.List[str]]] = {}

        self.configuration = configuration
        self.base_dir = base_dir

    def combine_features(self, report: CoverageReport) -> None:
        """Combine features of report with self."""
        for filename_a, filename_b in zip(self.tree, report.tree):
            assert Path(filename_a).name == Path(filename_b).name

            code_region_a = self.tree[filename_a]
            code_region_b = report.tree[filename_b]

            code_region_a.combine_features(code_region_b)

    def annotate_covered(self, configuration: Configuration) -> None:
        """Adds the presence condition to all covered code regions."""

        for filename in self.tree:
            code_region = self.tree[filename]
            code_region.annotate_covered(configuration)

    def _extract_feature_option_mapping(self, xml_file: Path) -> None:
        with local.cwd(Path(__file__).parent.parent.parent.parent.parent):
            output = local["feature_option_mapping.py"](xml_file)
        self.featue_option_mapping = json.loads(output)
        print(self.featue_option_mapping)

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
                    if not feature.startswith(
                        "__CONDITION__:"
                    ) and feature != "":
                        features.append(feature)
                instr_index = int(row["instr_index"])
                instr = row["instr"]
                vara_instr = VaraInstr(
                    kind, Path(source_file), line, column, features,
                    instr_index, instr
                )
                # Convert absolute paths to relative paths when possible
                try:
                    relative_path = Path(source_file).relative_to(
                        self.absolute_path
                    )
                    source_file = str(relative_path)
                except ValueError:
                    pass
                if source_file in self.tree:
                    code_region_tree = self.tree[source_file]
                    feature_node = code_region_tree.find_code_region(
                        location.line, location.column
                    )
                    if feature_node is not None:
                        feature_node.vara_instrs.append(vara_instr)
                #else:
                #    files = list(self.tree)
                #    print(
                #        "WARNING Ignoring VaRA instructions!:",
                #        f"'{source_file}' not in {files}"
                #    )

    def _import_functions(
        self, json_file: Path, tree: FilenameRegionMapping
    ) -> FilenameRegionMapping:
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
        self.absolute_path = absolute_path
        data: tp.Dict[str, tp.Any] = coverage_json["data"][0]
        # files: tp.List = data["files"]
        functions: tp.List[tp.Any] = data["functions"]
        totals: tp.Dict[str, tp.Any] = data["totals"]

        # Print all filenames in functions
        #for function in functions:
        #    print(function["name"], function["filenames"][0])

        for function in functions:
            name: str = function["name"]
            # count: int = function["count"]
            # branches: list = function["branches"]
            filenames: tp.List[str] = function["filenames"]
            relative_filenames = []
            for filename in filenames:
                relative_filenames.append(
                    str(Path(filename).relative_to(absolute_path))
                )

            regions: tp.List[tp.List[int]] = function["regions"]

            tree = self._import_code_regions(
                name, relative_filenames, regions, tree
            )

        # sanity checking
        self.__region_import_sanity_check(totals, tree)

        return tree.sorted()

    def _import_code_regions(
        self, function: str, filenames: tp.List[str],
        regions: tp.List[tp.List[int]], tree: FilenameRegionMapping
    ) -> FilenameRegionMapping:

        for region in regions:
            code_region = CodeRegion.from_list(region, function, filenames)
            tree.add(code_region)

        return tree

    def __region_import_sanity_check(
        self, totals: tp.Dict[str, tp.Any], tree: FilenameRegionMapping
    ) -> None:
        total_instantiations_count: int = totals["instantiations"]["count"]
        total_regions_count: int = totals["regions"]["count"]
        #total_regions_covered: int = totals["regions"]["covered"]
        #total_regions_notcovered: int = totals["regions"]["notcovered"]

        counted_code_regions = 0
        covered_regions = 0
        notcovered_regions = 0

        instantiations = set()

        for filename in tree:
            code_region = tree[filename]
            for region in code_region.iter_breadth_first():
                if region.kind != CodeRegionKind.FILE_ROOT:
                    instantiations.update(region.instantiations)
                if region.kind == CodeRegionKind.CODE:
                    counted_code_regions += 1
                    if region.is_covered():
                        covered_regions += 1
                    else:
                        notcovered_regions += 1

        print(len(instantiations), "==?", total_instantiations_count)
        #assert len(instantiations) == total_instantiations_count
        print(counted_code_regions, "==?", total_regions_count)
        #assert counted_code_regions == total_regions_count
        assert counted_code_regions != 0
        #assert covered_regions == total_regions_covered
        #assert notcovered_regions == total_regions_notcovered

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CoverageReport):
            return False
        for filename_a, filename_b in zip(self.tree, other.tree):
            if (Path(filename_a).name == Path(filename_b).name
               ) and (self.tree[filename_a] == other.tree[filename_b]):
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

        return json.dumps(self.tree, cls=EnhancedJSONEncoder)


Count = tp.Optional[int]
LinePart = str
CoverageFeatures = tp.Optional[str]
VaraFeatures = tp.Optional[tp.Set[str]]
Segment = tp.Tuple[Count, LinePart, CoverageFeatures, VaraFeatures]
Segments = tp.List[Segment]
SegmentBuffer = tp.DefaultDict[int, Segments]
FileSegmentBufferMapping = tp.Mapping[str, SegmentBuffer]


def cov_segments(
    report: CoverageReport,
    base_dir: Path,
) -> FileSegmentBufferMapping:
    """Returns the all segments for this report."""
    file_segments_mapping = {}
    for file in list(report.tree):
        region = report.tree[file]
        path = Path(file)
        file_segments_mapping[file] = _cov_segments_file(path, base_dir, region)

    return file_segments_mapping


def _cov_segments_file(
    rel_path: Path,
    base_dir: Path,
    region: CodeRegion,
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
    segments_dict = _cov_segments_function(region, lines, segments_dict)

    # Add rest of file
    segments_dict = __cov_fill_buffer(
        end_line=len(lines),
        end_column=len(lines[len(lines)]) + 1,
        count=None,
        cov_features=None,
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
    vara_features: str


def __table_to_text(
    table: tp.Dict[int, TableEntry],
    show_counts: bool = True,
    show_coverage_features: bool = False,
    show_vara_features: bool = False,
) -> str:
    output = []
    for line_number, entry in table.items():
        line = []
        line.append(f"{line_number:>5}")
        if show_counts:
            line.append(f"|{entry.count:>7}")

        # Set tabs to size
        text = entry.text.replace("\t", " " * TAB_SIZE)
        text = text.replace("\n", "", 1)
        if not any([show_coverage_features, show_vara_features]):
            line.append(f"|{text}")
        else:
            text = text[:CUTOFF_LENGTH]
            line.append(f"|{text:<{CUTOFF_LENGTH}}")
        if show_coverage_features:
            line.append(f"|{entry.coverage_features}")
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
            segments[-1] = (None, segments[-1][1], None, None
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
        vara_features = filter_out_nones(segment[3] for segment in segments)

        table[line_number] = TableEntry(
            count,
            "".join(colored_texts),
            __feature_text([coverage_features]),
            #list(coverage_features),
            __feature_text(vara_features),
        )

    return table


def __feature_text(iterable: tp.Iterable[tp.Iterable[str]]) -> str:
    feature_buffer = set()
    for x in iterable:
        for feature in x:
            if feature == "":
                # Ignore empty buffer entries
                continue
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
    if not (region.start.line == 1 and region.start.column == 1):
        # Add lines before region.
        prev_line, prev_column = __get_previous_line_and_column(
            region.start.line, region.start.column, lines
        )
        buffer = __cov_fill_buffer(
            end_line=prev_line,
            end_column=prev_column,
            count=None,
            cov_features=None,
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
                count=region.count
                if region.kind != CodeRegionKind.FILE_ROOT else None,
                cov_features=region.coverage_features(),
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
        count=region.count if region.kind != CodeRegionKind.FILE_ROOT else None,
        cov_features=region.coverage_features(),
        vara_features=region.vara_features(),
        lines=lines,
        buffer=buffer
    )

    return buffer


def __cov_fill_buffer(
    end_line: int, end_column: int, count: Count,
    cov_features: CoverageFeatures, vara_features: VaraFeatures,
    lines: tp.Dict[int, str], buffer: SegmentBuffer
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

        buffer[line_number].append((count, text, cov_features, vara_features))

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

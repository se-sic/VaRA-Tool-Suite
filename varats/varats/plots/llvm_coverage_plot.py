"""Display the coverage data."""

from __future__ import annotations

import gc
import json
import os
import typing as tp
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from functools import reduce
from multiprocessing import get_context
from pathlib import Path

import pandas as pd
from dd.autoref import Function  # type: ignore [import]

try:
    from dd.cudd import BDD  # type: ignore [import]
except ModuleNotFoundError:
    from dd.autoref import BDD  # type: ignore [import]

from plumbum import local, ProcessExecutionError

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CodeRegionKind,
    RegionEnd,
    RegionStart,
    CoverageReport,
    cov_segments,
    cov_show_segment_buffer,
    create_bdd,
    MeasureTime,
    FileSegmentBufferMapping,
)
from varats.experiment.experiment_util import ZippedReportFolder
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_EXPERIMENT_TYPE,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import FullCommitHash, RepositoryAtCommit

ADDITIONAL_FEATURE_OPTION_MAPPING: tp.Dict[str, tp.Union[str,
                                                         tp.List[str]]] = {}

TIMEOUT_SECONDS = 120

_IN = tp.TypeVar("_IN")
_OUT = tp.TypeVar("_OUT")

INGORE_PARSING_CODE = [
    CodeRegion(
        start=RegionStart(line=9, column=1),
        end=RegionEnd(line=17, column=2),
        count=-1,
        kind=CodeRegionKind.FILE_ROOT,
        function="isFeatureEnabled",
        filename="include/fpcsc/perf_util/feature_cmd.h"
    ),
    CodeRegion(
        start=RegionStart(line=42, column=1),
        end=RegionEnd(line=49, column=2),
        count=-1,
        kind=CodeRegionKind.FILE_ROOT,
        function="loadConfigFromArgv",
        filename="src/SimpleFeatureInteraction/SFImain.cpp"
    )
]

IGNORE_FEATURE_DEPENDENT_FUNCTIONS = [
    CodeRegion(
        start=RegionStart(line=19, column=1),
        end=RegionEnd(line=35, column=2),
        count=-1,
        kind=CodeRegionKind.FILE_ROOT,
        function="compress+addPadding+encrypt",
        filename="src/SimpleFeatureInteraction/SFImain.cpp"
    )
]


def _init_process() -> None:
    from signal import SIGTERM  # pylint: disable=import-outside-toplevel

    from pyprctl import set_pdeathsig  # pylint: disable=import-outside-toplevel

    set_pdeathsig(SIGTERM)
    gc.enable()


def optimized_map(
    func: tp.Callable[[_IN], _OUT],
    iterable: tp.Iterable[tp.Any],
    count: int = os.cpu_count() or 1,
    timeout: tp.Optional[int] = TIMEOUT_SECONDS
) -> tp.Iterable[_OUT]:
    """Optimized map function."""

    todo = list(iterable)
    todo_len = len(todo)
    if todo_len <= 1 or count == 1:
        return map(func, todo)

    cpu_count = os.cpu_count()
    assert cpu_count
    max_workers = min(cpu_count, todo_len)
    executor = ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_init_process,
        mp_context=get_context("forkserver")
    )
    result = list(
        executor.map(
            func,
            todo,
            timeout=timeout *
            (todo_len / min(count, todo_len)) if timeout is not None else None,
        )
    )
    executor.shutdown()
    del executor
    return result


def get_option_names(configuration: Configuration) -> tp.Iterable[str]:
    return map(lambda option: option.name, configuration.options())


def contains(configuration: Configuration, name: str, value: tp.Any) -> bool:
    """Test if a the specified configuration options bool(value) matches
    value."""
    for option in configuration.options():
        if option.name == name and bool(option.value) == value:
            return True
    return False


def available_features(
    objs: tp.Union[tp.Iterable[CoverageReport], tp.Iterable[Configuration]]
) -> tp.Set[str]:
    """Returns available features in all reports."""
    result = set()
    for obj in objs:
        config = obj if isinstance(obj, Configuration) else obj.configuration
        if config is not None:
            for feature in get_option_names(config):
                result.add(feature)
    return result


def coverage_missed_features(features: tp.Set[str],
                             code_region: CodeRegion) -> tp.Set[str]:
    return features.difference(code_region.coverage_features_set())


def coverage_found_features(
    features: tp.Set[str], code_region: CodeRegion
) -> bool:
    """Are features found by coverage data?"""
    if not features:
        return False
    return len(coverage_missed_features(features, code_region)) == 0


def vara_found_features(
    features: tp.Set[str], code_region: CodeRegion, threshold: float,
    feature_name_map: tp.Dict[str, tp.Set[str]]
) -> bool:
    """Are features found by VaRA?"""
    if not 0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0.")
    if not features:
        return False

    _vara_features = set()
    for feature in features:
        _vara_features.update(feature_name_map[feature])
    return 0 < code_region.features_threshold(_vara_features) >= threshold


def vara_features(
    region: CodeRegion, feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float
) -> tp.Set[str]:
    """Features found by VaRA."""
    found_vara_features = set()
    for feature in region.vara_features():
        if 0 < region.features_threshold([feature]) >= threshold:
            found_vara_features.update(feature_name_map[feature])
    return found_vara_features


def coverage_vara_features_combined(
    region: CodeRegion, feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float
) -> tp.Set[str]:
    """Features found by coverage data and VaRA combined."""
    found_vara_features = vara_features(region, feature_name_map, threshold)
    return region.coverage_features_set().union(found_vara_features)


def _matrix_analyze_code_region(
    feature: str, code_region: CodeRegion,
    feature_name_map: tp.Dict[str, tp.Set[str]], threshold: float, file: str,
    coverage_feature_regions: tp.List[tp.Any],
    coverage_normal_regions: tp.List[tp.Any],
    vara_feature_regions: tp.List[tp.Any], vara_normal_regions: tp.List[tp.Any]
) -> None:
    for region in code_region.iter_breadth_first():
        # Skip ignored regions
        if region.ignore:
            continue
        if feature == "__coverage__":
            # Only consider coverage features
            features = region.coverage_features_set()
        elif feature == "__vara__":
            # Only consider vara features.
            features = vara_features(region, feature_name_map, threshold)
        elif feature == "__both__":
            # Compare all coverage and all vara features with each other
            features = coverage_vara_features_combined(
                region, feature_name_map, threshold
            )
        else:
            # Consider only single feature
            features = {feature}

        feature_entry = ConfusionEntry(
            str(features), file, region.function, region.start.line,
            region.start.column, region.end.line, region.end.column
        )

        if coverage_found_features(features, region):
            coverage_feature_regions.append(feature_entry)
        else:
            coverage_normal_regions.append(feature_entry)
        if vara_found_features(features, region, threshold, feature_name_map):
            vara_feature_regions.append(feature_entry)
        else:
            vara_normal_regions.append(feature_entry)


def _compute_confusion_matrix(
    feature: str,
    feature_report: CoverageReport,
    feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float = 1.0
) -> ConfusionMatrix[ConfusionEntry]:
    coverage_feature_regions: tp.List[tp.Any] = []
    coverage_normal_regions: tp.List[tp.Any] = []
    vara_feature_regions: tp.List[tp.Any] = []
    vara_normal_regions: tp.List[tp.Any] = []

    for file, code_region in feature_report.tree.items():
        _matrix_analyze_code_region(
            feature, code_region, feature_name_map, threshold, file,
            coverage_feature_regions, coverage_normal_regions,
            vara_feature_regions, vara_normal_regions
        )

    return ConfusionMatrix(
        actual_positive_values=coverage_feature_regions,
        actual_negative_values=coverage_normal_regions,
        predicted_positive_values=vara_feature_regions,
        predicted_negative_values=vara_normal_regions
    )


def _compute_total_confusion_matrix(
    features: tp.List[str],
    feature_report: CoverageReport,
    feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float = 1.0
) -> ConfusionMatrix[ConfusionEntry]:
    coverage_feature_regions: tp.List[tp.Any] = []
    coverage_normal_regions: tp.List[tp.Any] = []
    vara_feature_regions: tp.List[tp.Any] = []
    vara_normal_regions: tp.List[tp.Any] = []

    for feature in features:
        for file, code_region in feature_report.tree.items():
            _matrix_analyze_code_region(
                feature, code_region, feature_name_map, threshold, file,
                coverage_feature_regions, coverage_normal_regions,
                vara_feature_regions, vara_normal_regions
            )

    return ConfusionMatrix(
        actual_positive_values=coverage_feature_regions,
        actual_negative_values=coverage_normal_regions,
        predicted_positive_values=vara_feature_regions,
        predicted_negative_values=vara_normal_regions
    )


def _extract_feature_option_mapping(
    xml_file: Path
) -> tp.Dict[str, tp.Union[str, tp.List[str]]]:
    with local.cwd(Path(__file__).parent.parent.parent.parent):
        try:
            output = local["myscripts/feature_option_mapping.py"](xml_file)
        except ProcessExecutionError as err:
            # vara-feature probably not installed
            print(err)
            return {}
    return json.loads(output)  # type: ignore [no-any-return]


def __parse_dnf_str_to_func(dnf: str, bdd: BDD) -> Function:
    or_parts = dnf.split("|")
    ands = []
    for and_str in or_parts:
        and_parts = and_str.strip().lstrip("(").rstrip(")").split("&")
        and_expr = []
        for var_str in and_parts:
            var = var_str.strip().split("~")
            if len(var) == 1:
                bdd.declare(var[0])
                variable = bdd.var(var[0])
                and_expr.append(variable)
            elif len(var) == 2 and var[0] == "":
                bdd.declare(var[1])
                variable = bdd.var(var[1])
                and_expr.append(~variable)
            else:
                raise ValueError(f"Invalid variable: {var}")
        ands.append(reduce(lambda x, y: x & y, and_expr))

    return reduce(lambda x, y: x | y, ands)


def _extract_feature_model_formula(xml_file: Path) -> Function:
    bdd = create_bdd()
    with local.cwd(Path(__file__).parent.parent.parent.parent):
        try:
            output = local["myscripts/feature_model_formula.py"](
                xml_file, timeout=TIMEOUT_SECONDS
            )
        except ProcessExecutionError as err:
            # vara-feature probably not installed
            print(err)
            return bdd.true

    func = __parse_dnf_str_to_func(output, bdd)
    if func == bdd.false:
        raise ValueError("Feature model equals false!")
    return func


def _config_to_func(config: Configuration) -> Function:
    bdd = create_bdd()
    func = bdd.true
    for option in config.options():
        bdd.declare(option.name)
        var = bdd.var(option.name)
        if option.value:
            func &= var
        else:
            func &= ~var
    return func


def _annotate_covered(
    args: tp.Tuple[CoverageReport, frozenset[str], tp.Dict[str, tp.Set[str]]]
) -> CoverageReport:
    report, all_options, feature_option_mapping = args
    configuration = report.configuration
    assert configuration is not None

    # Set not set features in configuration to false
    for option in all_options:
        if option not in get_option_names(configuration):
            # Exclude options with other values already set
            features = list(feature_option_mapping[option])
            if features:
                assert len(features) == 1
                options = feature_option_mapping[features[0]]
                if len(options) > 1:
                    continue
            configuration.set_config_option(option, False)

    report.annotate_covered(_config_to_func(configuration))

    return report


class CoverageReports:
    """Helper class to work with a list of coverage reports."""

    def __init__(self, reports: tp.List[CoverageReport]) -> None:
        super().__init__()

        # Check if all equal
        if not reports:
            raise ValueError("No reports given!")

        self.available_features = frozenset(available_features(reports))
        self._feature_model: tp.Optional[Function] = None
        self._feature_option_mapping: tp.Optional[tp.Dict[str,
                                                          tp.Set[str]]] = None
        self._feature_report: tp.Optional[CoverageReport] = None

        # Check all reports have same feature model
        self._reports = reports
        self._reference = self._reports[0]
        for report in self._reports[1:]:
            if self._reference.feature_model_xml != report.feature_model_xml:
                raise ValueError(
                    "CoverageReports have different feature models!"
                )

        feature_option_mapping = self.feature_option_mapping()
        to_process = [(report, self.available_features, feature_option_mapping)
                      for report in reports]

        self._reports = list(map(
            _annotate_covered,
            to_process,
        ))
        self._reference = self._reports[0]

    def __bidirectional_map(
        self, mapping: tp.Dict[str, tp.Union[str, tp.List[str]]]
    ) -> tp.Dict[str, tp.Set[str]]:
        result = defaultdict(set)
        for key, value in list(mapping.items()):
            if isinstance(value, list):
                for x in value:
                    result[key].add(x.lstrip("-"))
                    result[x.lstrip("-")].add(key)
            else:
                result[key].add(value.lstrip("-"))
                result[value.lstrip("-")].add(key)
        print(f"Bidirectional FeatureOptionMapping: {result}")
        return result

    def feature_option_mapping(
        self,
        additional_info: tp.Optional[tp.Dict[str,
                                             tp.Union[str,
                                                      tp.List[str]]]] = None
    ) -> tp.Dict[str, tp.Set[str]]:
        """Converts feature model mapping to biderectional mapping."""
        if self._feature_option_mapping is not None and additional_info is None:
            return self._feature_option_mapping

        mapping = {}
        if additional_info:
            mapping.update(additional_info)

        with MeasureTime("FeatureOptionMapping", "Extracting..."):
            with self._reference.create_feature_xml() as xml_file:
                feature_option_mapping = _extract_feature_option_mapping(
                    xml_file
                )

        mapping.update(feature_option_mapping)
        self._feature_option_mapping = self.__bidirectional_map(mapping)
        return self._feature_option_mapping

    def feature_model(self) -> Function:
        """Returns feature model for coverage reports."""
        if self._feature_model is not None:
            return self._feature_model

        with MeasureTime("FeatureModelFormula", "Extracting..."):
            with self._reference.create_feature_xml() as xml_file:
                self._feature_model = _extract_feature_model_formula(xml_file)

        return self._feature_model

    def feature_report(
        self,
        ignore_conditions: bool = True,
        ignore_parsing_code: bool = True,
        ignore_feature_dependent_functions: bool = True,
    ) -> CoverageReport:
        """Creates a Coverage Report with all features annotated."""
        if self._feature_report is not None:
            result = self._feature_report
        else:
            with MeasureTime("FeatureReport", "Calculating..."):
                result = reduce(
                    lambda x, y: x.combine_features(y), self._reports
                )
            result.feature_model = self.feature_model()

        result.parse_instrs(ignore_conditions)
        result.clean_ignored_regions()

        ignore_regions = []
        if ignore_parsing_code:
            ignore_regions.extend(INGORE_PARSING_CODE)
        if ignore_feature_dependent_functions:
            ignore_regions.extend(IGNORE_FEATURE_DEPENDENT_FUNCTIONS)

        if ignore_regions:
            result.mark_regions_ignored(ignore_regions)

        if self._feature_report is None:
            self._feature_report = result

        return result

    def feature_segments(
        self, base_dir: Path, **kwargs: tp.Any
    ) -> FileSegmentBufferMapping:
        """Returns segments annotated with corresponding feature
        combinations."""

        feature_report = self.feature_report(**kwargs)
        assert feature_report.feature_model is not None

        return cov_segments(feature_report, base_dir)

    def confusion_matrices(
        self,
        feature_name_map: tp.Dict[str, tp.Set[str]],
        threshold: float = 1.0,
        **kwargs: tp.Any
    ) -> tp.Dict[str, ConfusionMatrix[ConfusionEntry]]:
        """Returns the confusion matrices."""

        report = self.feature_report(**kwargs)

        result = {}
        # Iterate over feature_report and compare vara to coverage features
        features = sorted(self.available_features)
        for feature in features:
            result[feature] = _compute_confusion_matrix(
                feature, report, feature_name_map, threshold
            )

        # Sanity checking all matrices have equal number of code regions
        numbers = set()
        for matrix in result.values():
            total = 0
            total += matrix.TP
            total += matrix.TN
            total += matrix.FP
            total += matrix.FN
            numbers.add(total)
        assert len(numbers) == 1

        result["TOTAL"] = _compute_total_confusion_matrix(
            features, report, feature_name_map, threshold
        )

        result["all-coverage"] = _compute_confusion_matrix(
            "__coverage__", report, feature_name_map, threshold
        )

        result["all-vara"] = _compute_confusion_matrix(
            "__vara__", report, feature_name_map, threshold
        )

        result["all-both"] = _compute_confusion_matrix(
            "__both__", report, feature_name_map, threshold
        )

        print(result)
        return result


@dataclass(frozen=True)
class ConfusionEntry:
    """Entry in confusion matrix."""
    feature: str
    file: str
    function: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


BinaryReportsMapping = tp.NewType(
    "BinaryReportsMapping", tp.DefaultDict[str, tp.List[CoverageReport]]
)


def _process_report_file(
    args: tp.Tuple[ConfigurationMap, ReportFilepath, Path]
) -> tp.Tuple[str, CoverageReport]:
    config_map, report_filepath, base_dir = args

    binary = report_filepath.report_filename.binary_name
    config_id = report_filepath.report_filename.config_id
    if config_id is None:
        raise ValueError("config_id is None!")

    with MeasureTime(f"Config ID {config_id}", "Parsing..."):
        config = config_map.get_configuration(config_id)
        if config is None:
            raise ValueError("config is None!")

        coverage_report = CoverageReport.from_report(
            report_filepath.full_path(),
            config,
            base_dir,
        )
    return binary, coverage_report


def _save_plot(
    reports: CoverageReports, binary_dir: Path, base_dir: Path,
    **workarounds: bool
) -> None:
    name = "enabled_workarounds"
    text = ', '.join(
        workaround for workaround, value in workarounds.items() if value
    ).replace('_', '-')

    workaround_dir = (binary_dir / f"{name}: {text}")
    workaround_dir.mkdir(parents=True)

    feature_annotations = \
        workaround_dir / "feature_annotations.txt"

    _plot_coverage_annotations(
        reports, base_dir, feature_annotations, workarounds
    )

    print(
        cov_show_segment_buffer(
            reports.feature_segments(base_dir, **workarounds),
            show_counts=False,
            show_coverage_features=True,
            show_coverage_feature_set=True,
            show_vara_features=True
        )
    )

    _plot_confusion_matrix(
        reports,
        workaround_dir,
        workarounds,
        columns={
            "TP": "\\ac{TP}",
            "FN": "\\ac{FN}",
            "FP": "\\ac{FP}",
            "TN": "\\ac{TN}",
            "accuracy": "_Accuracy (\\%)",
            "precision": "Precision (\\%)",
            "recall": "Recall (\\%)",
            "balanced_accuracy": "Balanced Accuracy (\\%)",
            "f1_score": "_F1 Score (\\%)",
        }
    )


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def __init__(
        self, plot_config: PlotConfig, *args: tp.List[tp.Any], **kwargs: tp.Any
    ) -> None:
        super().__init__(plot_config, *args, **kwargs)
        self.workarounds = [
            "ignore_conditions", "ignore_parsing_code",
            "ignore_feature_dependent_functions"
        ]

    def _get_binary_reports_map(
        self,
        case_study: CaseStudy,
        report_files: tp.List[ReportFilepath],
        base_dir: Path,
    ) -> tp.Optional[BinaryReportsMapping]:
        try:
            config_map = load_configuration_map_for_case_study(
                get_loaded_paper_config(), case_study,
                PlainCommandlineConfiguration
            )
        except StopIteration:
            return None

        binary_reports_map: BinaryReportsMapping = BinaryReportsMapping(
            defaultdict(list)
        )

        to_process = [
            (config_map, report_file, base_dir) for report_file in report_files
        ]

        processed = optimized_map(
            _process_report_file,
            to_process,
        )
        for binary, coverage_report in processed:
            binary_reports_map[binary].append(coverage_report)

        return binary_reports_map

    def plot(self, view_mode: bool) -> None:
        pass

    def save(self, plot_dir: Path, filetype: str = 'zip') -> None:
        if len(self.plot_kwargs["experiment_type"]) > 1:
            print(
                "Plot can currently only handle a single experiment, "
                "ignoring everything else."
            )

        case_study = self.plot_kwargs["case_study"]

        project_name = case_study.project_name

        report_files = get_processed_revisions_files(
            project_name,
            self.plot_kwargs["experiment_type"][0],
            CoverageReport,
            get_case_study_file_name_filter(case_study),
            only_newest=False,
        )

        revisions = defaultdict(list)
        for report_file in report_files:
            revision = report_file.report_filename.commit_hash
            revisions[revision].append(report_file)

        for revision in list(revisions):
            zip_file = plot_dir / self.plot_file_name("zip")
            with ZippedReportFolder(zip_file) as tmpdir:
                with RepositoryAtCommit(project_name, revision) as base_dir:
                    workarounds = dict(
                        (workaround, False) for workaround in self.workarounds
                    )
                    # Disable Python's GC to speed up plotting
                    gc.disable()
                    binary_reports_map = self._get_binary_reports_map(
                        case_study,
                        revisions[revision],
                        base_dir,
                    )

                    if not binary_reports_map:
                        raise ValueError(
                            "Cannot load configs for case study '" +
                            case_study.project_name + "'! " +
                            "Have you set configs in your case study file?"
                        )

                    tmp_dir = Path(tmpdir) / f"{revision}"
                    for binary in binary_reports_map:
                        reports = CoverageReports(binary_reports_map[binary])

                        binary_dir = tmp_dir / binary
                        for workaround in self.workarounds + [""]:
                            _save_plot(
                                reports, binary_dir, base_dir, **workarounds
                            )
                            if workaround:
                                workarounds[workaround] = True
                    # Allow binary_reports_map to be freed
                    del binary_reports_map
                    gc.enable()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


def _plot_coverage_annotations(
    reports: CoverageReports, base_dir: Path, outfile: Path,
    workarounds: tp.Dict[str, bool]
) -> None:
    with outfile.open("w") as output:
        output.write(
            cov_show_segment_buffer(
                reports.feature_segments(base_dir, **workarounds),
                show_counts=False,
                show_coverage_features=True,
                show_coverage_feature_set=True,
                show_vara_features=True,
                save_to_dir=outfile.with_name("feature_annotations")
            )
        )


def _get_matrix_fields(
    matrix: ConfusionMatrix[ConfusionEntry], fields: tp.List[str]
) -> tp.List[str]:
    result = []
    for field in fields:
        attribute = getattr(matrix, field)
        if hasattr(attribute, "__call__"):
            result.append(attribute() * 100)
        else:
            result.append(f"${attribute}$")
    return result


def _plot_confusion_matrix( # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    reports: CoverageReports,
    outdir: Path,
    workarounds: tp.Dict[str, bool],
    columns: tp.Optional[tp.Dict[str, str]] = None
) -> None:

    feature_option_mapping = reports.feature_option_mapping(
        ADDITIONAL_FEATURE_OPTION_MAPPING
    )

    for threshold in [0.0, 1.0]:
        if threshold == 0.0:
            threshold_text = f">{int(threshold*100)}"
        else:
            threshold_text = f"{int(threshold*100)}"
        cf_dir = outdir / f"threshold: {threshold_text}%"
        cf_dir.mkdir()

        matrix_dict = reports.confusion_matrices(
            feature_option_mapping, threshold, **workarounds
        )
        if not columns:
            columns = {
                "TP": "True Positives (TP)",
                "FN": "False Negatives (FN)",
                "FP": "False Positives (FP)",
                "TN": "True Negatives (TN)"
            }

        rows = []
        for feature in matrix_dict:
            outfile = cf_dir / f"{feature}.matrix"
            matrix = matrix_dict[feature]
            with outfile.open("w") as output:
                output.write(f"{matrix}\n")
                tps = [str(x) for x in matrix.getTPs()]
                output.write(f"True Positives:\n{chr(10).join(sorted(tps))}\n")
                tns = [str(x) for x in matrix.getTNs()]
                output.write(f"True Negatives:\n{chr(10).join(sorted(tns))}\n")
                fps = [str(x) for x in matrix.getFPs()]
                output.write(f"False Positives:\n{chr(10).join(sorted(fps))}\n")
                fns = [str(x) for x in matrix.getFNs()]
                output.write(f"False Negatives:\n{chr(10).join(sorted(fns))}\n")

            row: tp.List[tp.Union[str, int, float]] = [f"{feature}"]
            row.extend(_get_matrix_fields(matrix, list(columns)))
            rows.append(row)

        df = pd.DataFrame(
            columns=["Feature"] +
            list(value.lstrip("_") for value in columns.values()),
            data=rows
        )
        #df.set_index("Feature", inplace=True)
        #df.sort_index(inplace=True)

        base_dir = reports.feature_report().base_dir
        name = base_dir.name if base_dir is not None else 'Unknown'
        caption_text = f"{name}: "
        if workarounds:
            text = ', '.join(
                workaround for workaround in workarounds if workaround
            ).replace('_', '-')
            workaround_text = f"workarounds: {text}"
            caption_text += f"{workaround_text}, "
        threshold_percent = f"{int(threshold * 100)}"
        if threshold == 0.0:
            threshold_percent = f">{threshold_percent}"
        threshold_percent = f"\\qty{{{threshold_percent}}}{{\\percent}}"
        caption_text += f"threshold: {threshold_percent}."

        column_format = "l"
        for column_text in columns.values():
            if column_text.startswith("_"):
                column_format += "H"
            elif "%" in column_text:
                column_format += "S"
            else:
                column_format += "c"
        table = dataframe_to_table(
            df,
            table_format=TableFormat.LATEX_BOOKTABS,
            style=df.style.format(thousands=r"\,",
                                  precision=2).hide(axis=0
                                                   ).set_caption(caption_text),
            wrap_table=False,
            wrap_landscape=False,
            hrules=True,
            column_format=column_format,
            position="htbp",
            position_float="centering",
            label=f"table:{name}:{workaround_text}_{threshold}",
            siunitx=True,
        )

        # Add midline befor TOTAL and comment rows after total.
        table_lines = []
        found_total = False
        for line in table.splitlines():
            if "TOTAL" in line:
                found_total = True
                table_lines.append("\\midrule")
                table_lines.append(line)
            else:
                if found_total and "&" in line:
                    table_lines.append(f"%{line}")
                else:
                    table_lines.append(line)

        outfile = cf_dir / "cofusion_matrix_table.tex"
        outfile.write_text(data="\n".join(table_lines), encoding="utf-8")


class CoveragePlotGenerator(
    PlotGenerator,
    generator_name="coverage",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_MULTI_CASE_STUDY],
):
    """Generates repo-churn plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        result: tp.List[Plot] = []
        for case_study in self.plot_kwargs["case_study"]:
            plot_kwargs = deepcopy(self.plot_kwargs)
            plot_kwargs["case_study"] = deepcopy(case_study)
            result.append(CoveragePlot(self.plot_config, **plot_kwargs))
        return result

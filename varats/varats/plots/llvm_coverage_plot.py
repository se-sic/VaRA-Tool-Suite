"""Display the coverage data."""

from __future__ import annotations

import gc
import json
import os
import typing as tp
from collections import defaultdict
from concurrent.futures import Executor, ProcessPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from plumbum import local, ProcessExecutionError
from pyeda.inter import Expression, expr  # type: ignore

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CoverageReport,
    cov_segments,
    cov_show_segment_buffer,
    FileSegmentBufferMapping,
    minimize,
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

TIMEOUT_SECONDS = 30
ADDITIONAL_FEATURE_OPTION_MAPPING: tp.Dict[str, tp.Union[str,
                                                         tp.List[str]]] = {}

_IN = tp.TypeVar("_IN")
_OUT = tp.TypeVar("_OUT")


def _init_process() -> None:
    from signal import SIGTERM

    from pyprctl import set_pdeathsig

    set_pdeathsig(SIGTERM)
    gc.enable()


__EXECUTOR: tp.Optional[Executor] = None


def optimized_map(
    func: tp.Callable[[_IN], _OUT],
    iterable: tp.Iterable[tp.Any],
    count: int = os.cpu_count() or 1
) -> tp.Iterable[_OUT]:
    """Optimized map function."""

    todo = list(iterable)
    todo_len = len(todo)
    if todo_len <= 1 or count == 1:
        return map(func, todo)

    global __EXECUTOR
    if __EXECUTOR is None:
        __EXECUTOR = ProcessPoolExecutor(
            max_workers=min(todo_len, count), initializer=_init_process
        )
    result = __EXECUTOR.map(
        func,
        todo,
        timeout=TIMEOUT_SECONDS * (todo_len / count),
        chunksize=max(1,
                      int((todo_len / count) * 0.1) + 1)
    )
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

    vara_features = set()
    for feature in features:
        vara_features.update(feature_name_map[feature])
    return 0 < code_region.features_threshold(vara_features) >= threshold


def coverage_vara_features_combined(
    region: CodeRegion, feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float
) -> tp.Set[str]:
    """Features found by coverage data and VaRA combined."""
    found_vara_features = set()
    for feature in region.vara_features():
        if 0 < region.features_threshold([feature]) >= threshold:
            found_vara_features.update(feature_name_map[feature])
    return region.coverage_features_set().union(found_vara_features)


def _matrix_analyze_code_region(
    feature: tp.Optional[str], code_region: CodeRegion,
    feature_name_map: tp.Dict[str, tp.Set[str]], threshold: float, file: str,
    coverage_feature_regions: tp.List[tp.Any],
    coverage_normal_regions: tp.List[tp.Any],
    vara_feature_regions: tp.List[tp.Any], vara_normal_regions: tp.List[tp.Any]
) -> None:
    for region in code_region.iter_breadth_first():
        if feature is None:
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
    feature: tp.Optional[str],
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


def _extract_feature_model_formula(xml_file: Path) -> Expression:
    with local.cwd(Path(__file__).parent.parent.parent.parent):
        try:
            output = local["myscripts/feature_model_formula.py"](
                xml_file, timeout=TIMEOUT_SECONDS
            )
        except ProcessExecutionError as err:
            # vara-feature probably not installed
            print(err)
            return expr(True)

    expression = expr(output)
    if not expression.is_dnf():
        raise ValueError("Feature model is not in DNF!")
    if expression.equivalent(expr(False)):
        raise ValueError("Feature model equals false!")
    print(output)
    expression = minimize(expression)
    return expression


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

    report.annotate_covered(configuration)

    return report


class CoverageReports:
    """Helper class to work with a list of coverage reports."""

    def __init__(self, reports: tp.List[CoverageReport]) -> None:
        super().__init__()

        # Check if all equal
        if not reports:
            raise ValueError("No reports given!")

        self.available_features = frozenset(available_features(reports))
        self._feature_model: tp.Optional[Expression] = None
        self._feature_option_mapping: tp.Optional[tp.Dict[str,
                                                          tp.Set[str]]] = None

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

        self._reports = list(optimized_map(
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
        print(result)
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

        with self._reference.create_feature_xml() as xml_file:
            feature_option_mapping = _extract_feature_option_mapping(xml_file)

        mapping.update(feature_option_mapping)
        self._feature_option_mapping = self.__bidirectional_map(mapping)
        return self._feature_option_mapping

    def feature_model(self) -> Expression:
        """Returns feature model for coverage reports."""
        if self._feature_model is not None:
            return self._feature_model

        with self._reference.create_feature_xml() as xml_file:
            self._feature_model = _extract_feature_model_formula(xml_file)

        return self._feature_model

    def feature_report(self) -> CoverageReport:
        """Creates a Coverage Report with all features annotated."""

        result = deepcopy(self._reference)
        result.feature_model = self.feature_model()
        for report in self._reports[1:]:
            result.combine_features(report)

        return result

    def feature_segments(self, base_dir: Path) -> FileSegmentBufferMapping:
        """Returns segments annotated with corresponding feature
        combinations."""

        feature_report = self.feature_report()
        assert feature_report.feature_model is not None

        return cov_segments(feature_report, base_dir)

    def confusion_matrices(
        self,
        feature_name_map: tp.Dict[str, tp.Set[str]],
        threshold: float = 1.0
    ) -> tp.Dict[str, ConfusionMatrix[ConfusionEntry]]:
        """Returns the confusion matrices."""

        report = self.feature_report()

        result = {}
        # Iterate over feature_report and compare vara to coverage features
        for feature in sorted(self.available_features):
            result[feature] = _compute_confusion_matrix(
                feature, report, feature_name_map, threshold
            )
        result["__all__"] = _compute_confusion_matrix(
            None, report, feature_name_map, threshold
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
    args: tp.Tuple[ConfigurationMap, ReportFilepath, Path, bool]
) -> tp.Tuple[str, CoverageReport]:
    config_map, report_filepath, base_dir, ignore_conditions = args

    binary = report_filepath.report_filename.binary_name
    config_id = report_filepath.report_filename.config_id
    if config_id is None:
        raise ValueError("config_id is None!")

    config = config_map.get_configuration(config_id)
    if config is None:
        raise ValueError("config is None!")

    coverage_report = CoverageReport.from_report(
        report_filepath.full_path(), config, base_dir, ignore_conditions
    )
    return binary, coverage_report


def _save_plot(
    binary_reports_map: BinaryReportsMapping, tmp_dir: Path, base_dir: Path
) -> None:
    for binary in binary_reports_map:
        reports = CoverageReports(binary_reports_map[binary])

        binary_dir = tmp_dir / binary
        binary_dir.mkdir(parents=True)

        feature_annotations = \
            binary_dir / "feature_annotations.txt"

        _plot_coverage_annotations(reports, base_dir, feature_annotations)

        print(
            cov_show_segment_buffer(
                reports.feature_segments(base_dir),
                show_counts=False,
                show_coverage_features=True,
                show_vara_features=True
            )
        )

        _plot_confusion_matrix(
            reports,
            binary_dir,
            columns={
                "precision": "Precision",
                "recall": "Recall",
                "accuracy": "Accuracy",
                "balanced_accuracy": "Balanced Accuracy",
                "f1_score": "F1 Score",
            }
        )


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def __init__(
        self, plot_config: PlotConfig, *args: tp.List[tp.Any], **kwargs: tp.Any
    ) -> None:
        super().__init__(plot_config, *args, **kwargs)
        self.workarounds = ["ignore_conditions"]

    def _get_binary_reports_map(
        self,
        case_study: CaseStudy,
        report_files: tp.List[ReportFilepath],
        base_dir: Path,
        ignore_conditions: bool = True
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

        to_process = [(config_map, report_file, base_dir, ignore_conditions)
                      for report_file in report_files]

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
                    disabled = dict(
                        (workaround, False) for workaround in self.workarounds
                    )
                    name = "disabled_workarounds"
                    for workaround in self.workarounds + [""]:
                        # Disable Python's GC to speed up plotting
                        gc.disable()
                        binary_reports_map = self._get_binary_reports_map(
                            case_study, revisions[revision], base_dir,
                            **disabled
                        )

                        if not binary_reports_map:
                            raise ValueError(
                                "Cannot load configs for case study '" +
                                case_study.project_name + "'! " +
                                "Have you set configs in your case study file?"
                            )
                        tmp_dir = Path(
                            tmpdir
                        ) / f"{revision}" / f"{name}: {', '.join(disabled)}"
                        _save_plot(binary_reports_map, tmp_dir, base_dir)
                        if workaround:
                            del disabled[workaround]
                        # Allow binary_reports_map to be freed
                        del binary_reports_map
                        gc.enable()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


def _plot_coverage_annotations(
    reports: CoverageReports, base_dir: Path, outfile: Path
) -> None:
    with outfile.open("w") as output:
        output.write(
            cov_show_segment_buffer(
                reports.feature_segments(base_dir),
                show_counts=False,
                show_coverage_features=True,
                show_vara_features=True,
                save_to_dir=outfile.with_name("feature_annotations")
            )
        )


def _get_matrix_fields(
    matrix: ConfusionMatrix[ConfusionEntry], fields: tp.List[str]
) -> tp.List[tp.Union[int, float]]:
    result = []
    for field in fields:
        attribute = getattr(matrix, field)
        if hasattr(attribute, "__call__"):
            result.append(attribute())
        else:
            result.append(attribute)
    return result


def _plot_confusion_matrix(
    reports: CoverageReports,
    outdir: Path,
    columns: tp.Optional[tp.Dict[str, str]] = None
) -> None:

    feature_option_mapping = reports.feature_option_mapping(
        ADDITIONAL_FEATURE_OPTION_MAPPING
    )

    matrix_dict = reports.confusion_matrices(feature_option_mapping)
    if not columns:
        columns = {
            "TP": "True Positives (TP)",
            "FN": "False Negatives (FN)",
            "FP": "False Positives (FP)",
            "TN": "True Negatives (TN)"
        }

    rows = []
    for feature in matrix_dict:
        outfile = outdir / f"{feature}.matrix"
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

    df = pd.DataFrame(columns=["Feature"] + list(columns.values()), data=rows)
    df.set_index("Feature", inplace=True)
    df.sort_index(inplace=True)

    table = dataframe_to_table(
        df,
        table_format=TableFormat.LATEX_BOOKTABS,
        style=df.style.format(thousands=r"\,"),
        wrap_table=False,
        wrap_landscape=False,
        hrules=True
    )
    outfile = outdir / "cofusion_matrix_table.tex"
    outfile.write_text(data=table, encoding="utf-8")


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

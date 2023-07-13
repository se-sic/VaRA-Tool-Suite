"""Display the coverage data."""

from __future__ import annotations

import typing as tp
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
)
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CoverageReport,
    cov_segments,
    cov_show_segment_buffer,
    FileSegmentBufferMapping,
)
from varats.experiment.experiment_util import ZippedReportFolder
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_EXPERIMENT_TYPE,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import FullCommitHash, RepositoryAtCommit


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


class CoverageReports:
    """Helper class to work with a list of coverage reports."""

    def __init__(self, reports: tp.List[CoverageReport]) -> None:
        super().__init__()

        self._reports = reports
        self.available_features = frozenset(available_features(self._reports))

    def feature_report(self) -> CoverageReport:
        """Creates a Coverage Report with all features annotated."""

        result = deepcopy(self._reports[0])
        for report in self._reports[1:]:
            result.combine_features(report)

        return result

    def feature_segments(self, base_dir: Path) -> FileSegmentBufferMapping:
        """Returns segments annotated with corresponding feature
        combinations."""

        feature_report = self.feature_report()

        return cov_segments(feature_report, base_dir)

    def confusion_matrix(
        self,
        feature_name_map: tp.Dict[str, str],
        threshold: float = 1.0
    ) -> tp.Dict[str, ConfusionMatrix]:
        """Returns the confusion matrix."""

        report = self.feature_report()

        result = {}
        matrix_all = ConfusionMatrix()
        # Iterate over feature_report and compare vara to coverage features
        for feature in self.available_features:
            matrix_feature = ConfusionMatrix()
            for file, func_map in report.filename_function_mapping.items():
                for function, tree in func_map.items():
                    for region in tree.iter_breadth_first():
                        classification_feature = classify_feature(
                            feature, region, threshold, feature_name_map
                        )
                        matrix_feature.add(
                            classification_feature,
                            ConfusionEntry(
                                feature, file, function, region.start.line,
                                region.start.column, region.end.line,
                                region.end.column
                            )
                        )

                        classification_all = classify_all(
                            region, threshold, feature_name_map
                        )
                        matrix_all.add(
                            classification_all,
                            ConfusionEntry(
                                "__all__", file, function, region.start.line,
                                region.start.column, region.end.line,
                                region.end.column
                            )
                        )
            result[feature] = matrix_feature

        result["__all__"] = matrix_all

        return result


class Classification(Enum):
    """Classification in confusion matrix."""
    TRUE_POSITIVE = "TP"
    TRUE_NEGATIVE = "TN"
    FALSE_POSITIVE = "FP"
    FALSE_NEGATIVE = "FN"


def classify_feature(
    feature: str, code_region: CodeRegion, threshold: float,
    feature_name_map: tp.Dict[str, str]
) -> Classification:
    """Classify single feature."""
    # Convert_feature_name
    vara_feature_name = feature_name_map[feature]
    vara_found = code_region.features_threshold([vara_feature_name]
                                               ) >= threshold
    coverage_found = feature in code_region.coverage_features_set()

    if vara_found and coverage_found:
        return Classification.TRUE_POSITIVE
    if vara_found:
        return Classification.FALSE_POSITIVE
    if coverage_found:
        return Classification.FALSE_NEGATIVE
    return Classification.TRUE_NEGATIVE


def classify_all(
    code_region: CodeRegion, threshold: float, feature_name_map: tp.Dict[str,
                                                                         str]
) -> Classification:
    """Classify all given features at once."""
    features = code_region.vara_features()
    vara_features = features if code_region.features_threshold(
        features
    ) >= threshold else set()

    # Convert feature names
    coverage_features = set()
    for feature in code_region.coverage_features_set():
        coverage_features.add(feature_name_map[feature])

    if len(vara_features) > 0 or len(coverage_features) > 0:
        if vara_features == coverage_features:
            return Classification.TRUE_POSITIVE
        if len(vara_features.difference(coverage_features)) > 0:
            return Classification.FALSE_POSITIVE
        if len(coverage_features.difference(vara_features)) > 0:
            return Classification.FALSE_NEGATIVE
    return Classification.TRUE_NEGATIVE


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


@dataclass
class ConfusionMatrix:
    """Confusion matrix."""
    true_positive: tp.Set[ConfusionEntry] = field(default_factory=set)
    true_negative: tp.Set[ConfusionEntry] = field(default_factory=set)
    false_positive: tp.Set[ConfusionEntry] = field(default_factory=set)
    false_negative: tp.Set[ConfusionEntry] = field(default_factory=set)

    def add(
        self, classification: Classification, entry: ConfusionEntry
    ) -> None:
        """Add classified entry to confusion matrix."""
        if classification == Classification.TRUE_POSITIVE:
            self.true_positive.add(entry)
        elif classification == Classification.TRUE_NEGATIVE:
            self.true_negative.add(entry)
        elif classification == Classification.FALSE_POSITIVE:
            self.false_positive.add(entry)
        elif classification == Classification.FALSE_NEGATIVE:
            self.false_negative.add(entry)

    def accuracy(self) -> tp.Optional[float]:
        """Calculate accuracy."""
        numerator = (len(self.true_positive) + len(self.true_negative))
        denumerator = (
            len(self.true_positive) + len(self.true_negative) +
            len(self.false_positive) + len(self.false_negative)
        )
        if denumerator == 0:
            return None
        return numerator / denumerator

    def precision(self) -> tp.Optional[float]:
        """Calculate precision."""
        numerator = len(self.true_positive)
        denumerator = len(self.true_positive) + len(self.false_positive)
        if denumerator == 0:
            return None
        return numerator / denumerator

    def recall(self) -> tp.Optional[float]:
        """Calculate recall."""
        numerator = len(self.true_positive)
        denumerator = len(self.true_positive) + len(self.false_negative)
        if denumerator == 0:
            return None
        return numerator / denumerator

    def __str__(self) -> str:
        return f"""True Positives: {len(self.true_positive)}
True Negatives: {len(self.true_negative)}
False Positives: {len(self.false_positive)}
False Negatives: {len(self.false_negative)}

Accuracy: {self.accuracy()}
Precision: {self.precision()}
Recall: {self.recall()}
"""


BinaryReportsMapping = tp.NewType(
    "BinaryReportsMapping", tp.DefaultDict[str, tp.List[CoverageReport]]
)


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def _get_binary_reports_map(
        self, case_study: CaseStudy, report_files: tp.List[ReportFilepath]
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

        for report_filepath in report_files:
            binary = report_filepath.report_filename.binary_name
            config_id = report_filepath.report_filename.config_id
            assert config_id is not None

            config = config_map.get_configuration(config_id)
            assert config is not None

            # Set not set features in configuration to false
            for feature in available_features(config_map.configurations()):
                if feature not in get_option_names(config):
                    config.set_config_option(feature, False)

            coverage_report = CoverageReport.from_report(
                report_filepath.full_path(), config
            )
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
            binary_reports_map = self._get_binary_reports_map(
                case_study, revisions[revision]
            )

            if not binary_reports_map:
                raise ValueError(
                    "Cannot load configs for case study '" +
                    case_study.project_name + "'! " +
                    "Have you set configs in your case study file?"
                )

            with RepositoryAtCommit(project_name, revision) as base_dir:
                zip_file = plot_dir / self.plot_file_name("zip")
                with ZippedReportFolder(zip_file) as tmpdir:

                    for binary in binary_reports_map:
                        reports = CoverageReports(binary_reports_map[binary])

                        binary_dir = Path(tmpdir) / binary
                        binary_dir.mkdir()

                        feature_annotations = \
                            binary_dir / "feature_annotations.txt"

                        _plot_coverage_annotations(
                            reports, base_dir, feature_annotations
                        )

                        print(
                            cov_show_segment_buffer(
                                reports.feature_segments(base_dir),
                                show_counts=False,
                                show_coverage_features=True,
                                show_vara_features=True
                            )
                        )

                        _plot_confusion_matrix(reports, binary_dir)

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
                show_vara_features=True
            )
        )


def _plot_confusion_matrix(reports: CoverageReports, outdir: Path) -> None:

    matrix_dict = reports.confusion_matrix({
        "enc": "Encryption",
        "compress": "Compression"
    })

    for feature in matrix_dict:
        outfile = outdir / f"{feature}.matrix"
        with outfile.open("w") as output:
            output.write(str(matrix_dict[feature]))


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

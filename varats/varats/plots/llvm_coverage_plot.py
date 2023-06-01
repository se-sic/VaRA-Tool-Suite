"""Display the coverage data."""

from __future__ import annotations

import typing as tp
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from itertools import filterfalse
from pathlib import Path

from more_itertools import powerset

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
    FrozenConfiguration,
)
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CoverageReport,
    cov_show,
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


class ConfigCoverageReportMapping(tp.Dict[FrozenConfiguration, CoverageReport]):
    """Maps Configs to CoverageReports."""

    def __init__(
        self, dictionary: tp.Dict[FrozenConfiguration, CoverageReport]
    ) -> None:
        available_features = set()
        for config in dictionary:
            for feature in get_option_names(config):
                available_features.add(feature)
        self.available_features = frozenset(available_features)

        tmp = {}
        for configuration, report in dictionary.items():
            # Recreate configuration with missing features
            new_configuration = configuration.unfreeze()
            for option_name in available_features.difference(
                set(get_option_names(configuration))
            ):
                # Option was not given. Assume this corresponds to value False.
                new_configuration.set_config_option(option_name, False)
            new_configuration = new_configuration.freeze()
            tmp[new_configuration] = report

        super().__init__(tmp)

    def create_feature_filter(
        self, features: tp.Dict[str, bool]
    ) -> tp.Callable[[Configuration], bool]:
        """Create filter for the given features."""

        def feature_filter(config: Configuration) -> bool:
            """Filter all configs that contain the given features."""
            for feature, value in features.items():
                if not contains(config, feature, value):
                    return False
            return True

        return feature_filter

    def _get_configs_with_features(
        self, features: tp.Dict[str, bool]
    ) -> tp.List[FrozenConfiguration]:
        feature_filter = self.create_feature_filter(features)
        return list(filter(feature_filter, list(self)))

    def _get_configs_without_features(
        self, features: tp.Dict[str, bool]
    ) -> tp.List[FrozenConfiguration]:
        feature_filter = self.create_feature_filter(features)
        return list(filterfalse(feature_filter, list(self)))

    def diff(self, features: tp.Dict[str, bool]) -> CoverageReport:
        """Creates a coverage report by diffing all coverage reports that
        contain the given features with all that do not share them."""

        for feature in features:
            if feature not in self.available_features:
                raise ValueError(
                    f"No reports with feature '{feature}' available!"
                )

        configs_with_features = self._get_configs_with_features(features)
        configs_without_features = self._get_configs_without_features(features)

        _ = ",".join("\n" + str(x.options()) for x in configs_with_features)
        print(f"Configs with features:\n[{_}\n]")

        _ = ",".join(
            "\n" + str(set(x.options())) for x in configs_without_features
        )
        print(f"Configs without features:\n[{_}\n]")

        if len(configs_with_features
              ) == 0 or len(configs_without_features) == 0:
            raise ValueError(
                "Diff impossible! No reports with given features available!"
            )

        report_with_features = _merge_reports(
            list(deepcopy(self[x]) for x in configs_with_features)
        )

        result = _merge_reports(
            list(deepcopy(self[x]) for x in configs_without_features)
        )

        result.diff(
            report_with_features,
            features=[x for x, y in features.items() if y]
        )
        return result

    def merge_all(self) -> CoverageReport:
        """Merge all available Reports into one."""
        return _merge_reports(deepcopy(list(self.values())))

    def feature_report(self) -> CoverageReport:
        """Creates a Coverage Report with all features annotated."""
        diffs: tp.List[CoverageReport] = []
        for feature in self.available_features:
            print(feature)
            diffs.append(self.diff({feature: True}))

        result = deepcopy(diffs[0])
        for report in diffs[1:]:
            result.combine_features(report)

        return result

    def feature_segments(self, base_dir: Path) -> FileSegmentBufferMapping:
        """Returns segments annotated with corresponding feature
        combinations."""

        feature_report = self.feature_report()

        return cov_segments(feature_report, base_dir)

    def confusion_matrix(
        self, vara_coverage_features_map: tp.Dict[str, str]
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
                        coverage_features = region.coverage_features_set
                        # Map coverage to vara feature names
                        vara_features = set()
                        for vara_feature in region.vara_features:
                            vara_features.add(
                                vara_coverage_features_map[vara_feature]
                            )

                        classification_feature = classify_feature(
                            feature, vara_features, coverage_features
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
                            vara_features, coverage_features
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
    TRUE_POSITIVE = "TP"
    TRUE_NEGATIVE = "TN"
    FALSE_POSITIVE = "FP"
    FALSE_NEGATIVE = "FN"


def classify_feature(
    feature: str, vara_features: tp.Set[str], coverage_features: tp.Set[str]
) -> Classification:
    """Classify single feature."""
    if feature in vara_features and feature in coverage_features:
        return Classification.TRUE_POSITIVE
    elif feature in vara_features:
        return Classification.FALSE_POSITIVE
    elif feature in coverage_features:
        return Classification.FALSE_NEGATIVE
    return Classification.TRUE_NEGATIVE


def classify_all(
    vara_features: tp.Set[str], coverage_features: tp.Set[str]
) -> Classification:
    """Classify all features at once."""
    print(vara_features, coverage_features)
    if len(vara_features) > 0 or len(coverage_features) > 0:
        if vara_features == coverage_features:
            return Classification.TRUE_POSITIVE
        elif len(vara_features.difference(coverage_features)) > 0:
            return Classification.FALSE_POSITIVE
        elif len(coverage_features.difference(vara_features)) > 0:
            return Classification.FALSE_NEGATIVE
    return Classification.TRUE_NEGATIVE


@dataclass(frozen=True)
class ConfusionEntry:
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
        if classification == Classification.TRUE_POSITIVE:
            self.true_positive.add(entry)
        elif classification == Classification.TRUE_NEGATIVE:
            self.true_negative.add(entry)
        elif classification == Classification.FALSE_POSITIVE:
            self.false_positive.add(entry)
        elif classification == Classification.FALSE_NEGATIVE:
            self.false_negative.add(entry)
        else:
            raise NotImplemented("")

    def accuracy(self) -> tp.Optional[float]:
        numerator = (len(self.true_positive) + len(self.true_negative))
        denumerator = (
            len(self.true_positive) + len(self.true_negative) +
            len(self.false_positive) + len(self.false_negative)
        )
        if denumerator == 0:
            return None
        return numerator / denumerator

    def precision(self) -> tp.Optional[float]:
        numerator = len(self.true_positive)
        denumerator = len(self.true_positive) + len(self.false_positive)
        if denumerator == 0:
            return None
        return numerator / denumerator

    def recall(self) -> tp.Optional[float]:
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


BinaryConfigsMapping = tp.NewType(
    "BinaryConfigsMapping", tp.Dict[str, ConfigCoverageReportMapping]
)


def non_empty_powerset(iterable: tp.Iterable[tp.Any]) -> tp.Iterable[tp.Any]:
    """Powerset without empty set."""
    iterator = powerset(iterable)
    next(iterator)
    return iterator


def _merge_reports(reports: tp.Iterable[CoverageReport]) -> CoverageReport:
    reports = iter(reports)
    report = next(reports)
    for coverage_report in reports:
        report.merge(coverage_report)
    return report


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def _get_binary_config_map(
        self, case_study: CaseStudy, report_files: tp.List[ReportFilepath]
    ) -> tp.Optional[BinaryConfigsMapping]:
        try:
            config_map = load_configuration_map_for_case_study(
                get_loaded_paper_config(), case_study,
                PlainCommandlineConfiguration
            )
        except StopIteration:
            return None

        binary_config_map: tp.DefaultDict[str, tp.Dict[
            FrozenConfiguration, CoverageReport]] = defaultdict(dict)

        for report_filepath in report_files:
            binary = report_filepath.report_filename.binary_name
            config_id = report_filepath.report_filename.config_id
            assert config_id is not None

            coverage_report = CoverageReport.from_report(
                report_filepath.full_path()
            )
            config = config_map.get_configuration(config_id)
            assert config is not None
            binary_config_map[binary][config.freeze()] = coverage_report

        result = {}
        for binary in list(binary_config_map):
            result[binary] = ConfigCoverageReportMapping(
                binary_config_map[binary]
            )
        return BinaryConfigsMapping(result)

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
            binary_config_map = self._get_binary_config_map(
                case_study, revisions[revision]
            )

            if not binary_config_map:
                raise ValueError(
                    "Cannot load configs for case study '" +
                    case_study.project_name + "'! " +
                    "Have you set configs in your case study file?"
                )

            with RepositoryAtCommit(project_name, revision) as base_dir:
                zip_file = plot_dir / self.plot_file_name("zip")
                with ZippedReportFolder(zip_file) as tmpdir:

                    for binary in binary_config_map:
                        config_report_map = binary_config_map[binary]

                        binary_dir = Path(tmpdir) / binary
                        binary_dir.mkdir()

                        coverage_diff = binary_dir / "coverage_diff.txt"
                        _plot_coverage_diff(
                            config_report_map, base_dir, coverage_diff
                        )

                        coverage_annotations = \
                            binary_dir / "coverage_annotations.txt"
                        _plot_coverage_annotations(
                            config_report_map, base_dir, coverage_annotations
                        )

                        print(
                            cov_show_segment_buffer(
                                config_report_map.feature_segments(base_dir),
                                show_counts=False,
                                show_coverage_features=True
                            )
                        )

                        _plot_confusion_matrix(config_report_map, binary_dir)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


def _plot_coverage_diff(
    config_report_map: ConfigCoverageReportMapping, base_dir: Path,
    outfile: Path
) -> None:
    with outfile.open("w") as output:
        output.write("Code executed by all feature combinations\n")
        output.write(cov_show(config_report_map.merge_all(), base_dir))
        for features in non_empty_powerset(
            config_report_map.available_features
        ):
            output.write(f"Diff for '{features}':\n")
            diff = config_report_map.diff({
                feature: True for feature in features
            })
            output.write(cov_show(diff, base_dir))


def _plot_coverage_annotations(
    config_report_map: ConfigCoverageReportMapping, base_dir: Path,
    outfile: Path
) -> None:
    with outfile.open("w") as output:
        output.write(
            cov_show_segment_buffer(
                config_report_map.feature_segments(base_dir),
                show_counts=False,
                show_coverage_features=True
            )
        )


def _plot_confusion_matrix(
    config_report_map: ConfigCoverageReportMapping, outdir: Path
) -> None:

    matrix_dict = config_report_map.confusion_matrix({
        "Encryption": "enc",
        "Compression": "compress"
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

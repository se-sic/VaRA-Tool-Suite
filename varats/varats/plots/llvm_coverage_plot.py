"""Display the coverage data."""

from __future__ import annotations

import typing as tp
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
)
from varats.data.metrics import ConfusionMatrix as _ConfusionMatrix
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
    feature_name_map: tp.Dict[str, str]
) -> bool:
    """Are features found by VaRA?"""
    if not 0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0.")
    if not features:
        return False

    vara_features = {feature_name_map[feature] for feature in features}
    return 0 < code_region.features_threshold(vara_features) >= threshold


def coverage_vara_features_combined(
    region: CodeRegion, feature_name_map: tp.Dict[str, str], threshold: float
) -> tp.Set[str]:
    """Features found by coverage data and VaRA combined."""
    reverse_features = dict(
        (item[1], item[0]) for item in feature_name_map.items()
    )
    found_vara_features = set(
        reverse_features[feature]
        for feature in region.vara_features()
        if 0 < region.features_threshold([feature]) >= threshold
    )
    return region.coverage_features_set().union(found_vara_features)


def _matrix_analyze_code_region(
    feature: tp.Optional[str], tree: CodeRegion, feature_name_map: tp.Dict[str,
                                                                           str],
    threshold: float, file: str, coverage_feature_regions: tp.List[tp.Any],
    coverage_normal_regions: tp.List[tp.Any],
    vara_feature_regions: tp.List[tp.Any], vara_normal_regions: tp.List[tp.Any]
) -> None:
    for region in tree.iter_breadth_first():
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
    feature_name_map: tp.Dict[str, str],
    threshold: float = 1.0
) -> ConfusionMatrix:
    coverage_feature_regions: tp.List[tp.Any] = []
    coverage_normal_regions: tp.List[tp.Any] = []
    vara_feature_regions: tp.List[tp.Any] = []
    vara_normal_regions: tp.List[tp.Any] = []

    for file, func_map in feature_report.filename_function_mapping.items():
        for _, tree in func_map.items():
            _matrix_analyze_code_region(
                feature, tree, feature_name_map, threshold, file,
                coverage_feature_regions, coverage_normal_regions,
                vara_feature_regions, vara_normal_regions
            )

    return ConfusionMatrix(
        actual_positive_values=coverage_feature_regions,
        actual_negative_values=coverage_normal_regions,
        predicted_positive_values=vara_feature_regions,
        predicted_negative_values=vara_normal_regions
    )


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

    def confusion_matrices(
        self,
        feature_name_map: tp.Dict[str, str],
        threshold: float = 1.0
    ) -> tp.Dict[str, ConfusionMatrix]:
        """Returns the confusion matrices."""

        report = self.feature_report()

        result = {}
        # Iterate over feature_report and compare vara to coverage features
        for feature in self.available_features:
            result[feature] = _compute_confusion_matrix(
                feature, report, feature_name_map, threshold
            )
        result["__all__"] = _compute_confusion_matrix(
            None, report, feature_name_map, threshold
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


class ConfusionMatrix(_ConfusionMatrix):
    """Replace when VaRA's confusion matrix supports this."""

    def get_tp(self) -> tp.Set[tp.Any]:
        return set(self.__actual_positive_values
                  ).intersection(self.__predicted_positive_values)

    def get_tn(self) -> tp.Set[tp.Any]:
        return set(self.__actual_negative_values
                  ).intersection(self.__predicted_negative_values)

    def get_fp(self) -> tp.Set[tp.Any]:
        return set(self.__predicted_positive_values).difference(self.get_tp())

    def get_fn(self) -> tp.Set[tp.Any]:
        return set(self.__predicted_negative_values).difference(self.get_tn())

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"""True Positives: {self.TP}
{chr(10).join(str(x) for x in self.get_tp())}
True Negatives: {self.TN}
{chr(10).join(str(x) for x in self.get_tn())}
False Positives: {self.FP}
{chr(10).join(str(x) for x in self.get_fp())}
False Negatives: {self.FN}
{chr(10).join(str(x) for x in self.get_fn())}

Accuracy: {self.accuracy()}
Precision: {self.precision()}
Recall: {self.recall()}
Specifity: {self.specificity()}
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

    matrix_dict = reports.confusion_matrices({
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

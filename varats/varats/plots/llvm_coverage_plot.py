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
from varats.data.metrics import ConfusionMatrix
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

ADDITIONAL_FEATURE_OPTION_MAPPING: tp.Dict[str, str] = {}


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
    feature: tp.Optional[str], tree: CodeRegion,
    feature_name_map: tp.Dict[str, tp.Set[str]], threshold: float, file: str,
    coverage_feature_regions: tp.List[tp.Any],
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
    feature_name_map: tp.Dict[str, tp.Set[str]],
    threshold: float = 1.0
) -> ConfusionMatrix[ConfusionEntry]:
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

    def __bidirectional_map(
        self, mapping: tp.Dict[str, str]
    ) -> tp.Dict[str, tp.Set[str]]:
        result = defaultdict(set)
        for key, value in list(mapping.items()):
            if ";" in value:
                for x in value.split(";"):
                    result[key].add(x.lstrip("-"))
                    result[x.lstrip("-")].add(key)
            else:
                result[key].add(value.lstrip("-"))
                result[value.lstrip("-")].add(key)
        print(result)
        return result

    def feature_option_mapping(
        self,
        additional_information: tp.Optional[tp.Dict[str, str]] = None
    ) -> tp.Dict[str, tp.Set[str]]:
        """Converts feature model mapping to biderectional mapping."""
        # Check if all equal
        tmp = set(
            map(
                lambda x: tuple(x.featue_option_mapping.items()), self._reports
            )
        )
        if len(tmp) > 1:
            raise ValueError(
                "CoverageReports have used different feature models!"
            )
        mapping = {}
        if additional_information:
            mapping.update(additional_information)
        if len(tmp) == 1:
            mapping.update(self._reports[0].featue_option_mapping)
        return self.__bidirectional_map(mapping)

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
        feature_name_map: tp.Dict[str, tp.Set[str]],
        threshold: float = 1.0
    ) -> tp.Dict[str, ConfusionMatrix[ConfusionEntry]]:
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

    feature_option_mapping = reports.feature_option_mapping(
        ADDITIONAL_FEATURE_OPTION_MAPPING
    )

    matrix_dict = reports.confusion_matrices(feature_option_mapping)

    for feature in matrix_dict:
        outfile = outdir / f"{feature}.matrix"
        matrix = matrix_dict[feature]
        with outfile.open("w") as output:
            output.write(f"{matrix}\n")
            tps = [str(x) for x in matrix.getTPs()]
            output.write(f"True Positives:\n{chr(10).join(tps)}\n")
            tns = [str(x) for x in matrix.getTNs()]
            output.write(f"True Negatives:\n{chr(10).join(tns)}\n")
            fps = [str(x) for x in matrix.getFPs()]
            output.write(f"False Positives:\n{chr(10).join(fps)}\n")
            fns = [str(x) for x in matrix.getFNs()]
            output.write(f"False Negatives:\n{chr(10).join(fns)}\n")


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

"""Display the coverage data."""

from __future__ import annotations

import typing as tp
from collections import defaultdict
from copy import deepcopy
from itertools import filterfalse
from pathlib import Path

from more_itertools import powerset

from varats.base.configuration import (
    Configuration,
    PlainCommandlineConfiguration,
    FrozenConfiguration,
)
from varats.data.reports.llvm_coverage_report import (
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

    def feature_segments(self, base_dir: Path) -> FileSegmentBufferMapping:
        """Returns segments annotated with corresponding feature
        combinations."""

        # Get segments for all feature combinations.
        diffs: tp.List[CoverageReport] = []
        for features in non_empty_powerset(self.available_features):
            print(features)
            diffs.append(self.diff({feature: True for feature in features}))

        result = deepcopy(diffs[0])
        for report in diffs[1:]:
            result.combine_features(report)

        return cov_segments(result, base_dir)


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

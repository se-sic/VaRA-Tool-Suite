"""Display the coverage data."""

from __future__ import annotations

import typing as tp
from collections import defaultdict
from copy import deepcopy
from itertools import filterfalse

from more_itertools import powerset

from varats.base.configuration import (
    PlainCommandlineConfiguration,
    Configuration,
)
from varats.data.reports.llvm_coverage_report import CoverageReport
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_EXPERIMENT_TYPE,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import FullCommitHash

ConfigsCoverageReportMapping = tp.NewType(
    "ConfigsCoverageReportMapping", tp.Dict[Configuration, CoverageReport]
)

BinaryConfigsMapping = tp.NewType(
    "BinaryConfigsMapping", tp.DefaultDict[str, ConfigsCoverageReportMapping]
)


def get_options(configuration: Configuration) -> tp.List[str]:
    return [x.value for x in configuration.options()]


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


class RuntimeConfig:
    """All features that were enabled/disabled during one run."""

    def __init__(self, features: tp.Tuple[str, bool]) -> None:
        super().__init__()
        self.features: tp.FrozenSet[tp.Tuple[str, bool]] = frozenset(features)

    @classmethod
    def from_iterable(
        cls, enabled_features: tp.Iterable[str],
        disabled_features: tp.Iterable[str]
    ) -> RuntimeConfig:
        """RuntimeConfig from iterables."""
        runtime_config = []
        for feature in enabled_features:
            runtime_config.append((feature, True))
        for feature in disabled_features:
            runtime_config.append((feature, False))

        return cls(runtime_config)

    def keys(self) -> tp.Iterator[str]:
        for item in self:
            yield item[0]

    def values(self) -> tp.Iterator[bool]:
        for item in self:
            yield item[1]

    def items(self) -> tp.Iterator[tp.Tuple[str, bool]]:
        return iter(self)

    def get(self, feature: str) -> tp.Optional[bool]:
        """Returns either value of feature or None."""
        for item in self:
            if item[0] == feature:
                return item[1]

        return None

    def contains(self, feature: str, value: bool) -> bool:
        return (feature, value) in self

    def __iter__(self) -> tp.Iterator[tp.Tuple[str, bool]]:
        return iter(self.features)

    def __repr__(self) -> str:
        return str(self.features)


class CoverageFeatureDiffer:
    """Creates coverage diffs dependend on the given features."""

    def __init__(self, available_features: tp.Iterable[str]) -> None:
        super().__init__()
        self.available_features = frozenset(available_features)
        self.config_combinations: tp.Dict[tp.FrozenSet[RuntimeConfig],
                                          CoverageReport] = {}

    def _add(
        self, config_combinations: tp.List[tp.List[str]],
        coverage_report: CoverageReport
    ) -> None:
        runtime_configs = []
        for combination in config_combinations:
            for feature in combination:
                assert feature in self.available_features
            enabled_features = frozenset(combination)
            disabled_features = self.available_features.difference(
                enabled_features
            )
            runtime_config = RuntimeConfig.from_iterable(
                enabled_features=enabled_features,
                disabled_features=disabled_features
            )
            runtime_configs.append(runtime_config)
        self.config_combinations[frozenset(runtime_configs)] = coverage_report

    @classmethod
    def from_config_report_map(
        cls, config_report_map: ConfigsCoverageReportMapping
    ) -> CoverageFeatureDiffer:
        """Creates a CoverageFeatureDiffer instance from the given config report
        map."""
        available_features = set()
        for config in list(config_report_map):
            for feature in get_options(config):
                available_features.add(feature)

        print(available_features)
        coverage_feature_differ = cls(available_features)
        for config_set in non_empty_powerset(config_report_map.items()):
            configs = []
            reports = []
            for configuration, coverage_report in deepcopy(config_set):
                config_features = get_options(configuration)
                configs.append(config_features)
                reports.append(coverage_report)
            report = _merge_reports(reports)
            coverage_feature_differ._add(configs, report)

        return coverage_feature_differ

    def diff(self, features: tp.Dict[str, bool]) -> CoverageReport:
        """Creates a coverage report by diffing all coverage reports that
        contain the given features with all that do not share them."""

        def feature_filter(configs: tp.FrozenSet[RuntimeConfig]) -> bool:
            """filter all configs that contain the given features."""
            for config in configs:
                for feature, value in features.items():
                    if not config.contains(feature, value):
                        return False

            return True

        configs_with_features = filter(
            feature_filter, list(self.config_combinations)
        )

        configs_without_features = filterfalse(
            feature_filter, list(self.config_combinations)
        )

        print(
            f"Configs with features:\n{list(deepcopy(configs_with_features))}"
        )
        print(
            f"Configs without features:\n{list(deepcopy(configs_without_features))}"
        )

        report_with_features = _merge_reports(
            list(
                deepcopy(self.config_combinations[x])
                for x in configs_with_features
            )
        )
        report_without_features = _merge_reports(
            list(
                deepcopy(self.config_combinations[x])
                for x in configs_without_features
            )
        )

        report_with_features.diff(report_without_features)
        return report_with_features


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def _get_binary_config_map(
        self, case_study: CaseStudy
    ) -> BinaryConfigsMapping:
        project_name = case_study.project_name

        report_files = get_processed_revisions_files(
            project_name,
            self.plot_kwargs["experiment_type"][0],
            CoverageReport,
            get_case_study_file_name_filter(case_study),
            only_newest=False,
        )

        config_map = load_configuration_map_for_case_study(
            get_loaded_paper_config(), case_study, PlainCommandlineConfiguration
        )

        binary_config_map: BinaryConfigsMapping = BinaryConfigsMapping(
            defaultdict(lambda: ConfigsCoverageReportMapping({}))
        )

        for report_filepath in report_files:
            binary = report_filepath.report_filename.binary_name
            config_id = report_filepath.report_filename.config_id
            assert config_id is not None

            coverage_report = CoverageReport.from_report(
                report_filepath.full_path()
            )
            config = config_map.get_configuration(config_id)
            assert config is not None
            binary_config_map[binary][config] = coverage_report
        return binary_config_map

    def plot(self, view_mode: bool) -> None:
        if len(self.plot_kwargs["experiment_type"]) > 1:
            print(
                "Plot can currently only handle a single experiment, "
                "ignoring everything else."
            )

        case_study = self.plot_kwargs["case_study"]

        binary_config_map = self._get_binary_config_map(case_study)

        if not binary_config_map:
            raise Exception(
                "Cannot load configs for case study " +
                case_study.project_name + " !"
            )

        for binary in binary_config_map:
            config_report_map = binary_config_map[binary]

            coverage_feature_differ = CoverageFeatureDiffer.from_config_report_map(
                config_report_map
            )
            for feature in coverage_feature_differ.available_features:
                print(f"Diff for '{feature}':")
                diff = coverage_feature_differ.diff({feature: True})

                if diff:
                    pass

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CoveragePlotGenerator(
    PlotGenerator,
    generator_name="coverage",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_MULTI_CASE_STUDY]
):
    """Generates repo-churn plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        result: tp.List[Plot] = []
        for case_study in self.plot_kwargs["case_study"]:
            plot_kwargs = deepcopy(self.plot_kwargs)
            plot_kwargs["case_study"] = deepcopy(case_study)
            result.append(CoveragePlot(self.plot_config, **plot_kwargs))
        return result

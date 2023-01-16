"""Display the coverage data."""

import typing as tp
from collections import defaultdict
from itertools import chain, combinations

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

        loaded_paper_config = get_loaded_paper_config()
        case_studies = self.plot_kwargs["case_study"]

        for case_study in case_studies:
            binary_config_map = self._get_binary_config_map(case_study)

            if not binary_config_map:
                raise Exception(
                    f"Cannot load configs for case study '{case_study.project_name}'!"
                )

            #coverage_report.merge(coverage_report)
            for binary in binary_config_map:
                config_report_map = binary_config_map[binary]
                for config_set in self._powerset(config_report_map.keys()):
                    print(len(config_set), config_set)

    def _powerset(self, iterable: tp.Iterable[tp.Any]) -> tp.Iterable[tp.Any]:
        """
        Powerset without empty set.

        powerset([1,2,3]) --> (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

        Modified version of:
        https://docs.python.org/3/library/itertools.html#itertools-recipes
        """
        s = list(iterable)
        return chain.from_iterable(
            combinations(s, r) for r in range(1,
                                              len(s) + 1)
        )

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
        return [CoveragePlot(self.plot_config, **self.plot_kwargs)]

"""Display the coverage data."""

import typing as tp
from pathlib import Path

from varats.data.reports.llvm_coverage_report import CoverageReport
from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash


class CoveragePlot(Plot, plot_name="coverage"):
    """Plot to visualize coverage diffs."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        if len(self.plot_kwargs["experiment_type"]) > 1:
            print(
                "Plot can currently only handle a single experiment, "
                "ignoring everything else."
            )

        for case_study in case_studies:
            project_name = case_study.project_name

            report_files = get_processed_revisions_files(
                project_name, self.plot_kwargs["experiment_type"][0],
                WLCoverageReportAggregate,
                get_case_study_file_name_filter(case_study)
            )

            for report_filepath in report_files:
                coverage_report = WLCoverageReportAggregate(
                    report_filepath.full_path()
                )
                report_file = coverage_report.filename

                for workload_name in coverage_report.workload_names():
                    for wall_clock_time in \
                            coverage_report.measurements_wall_clock_time(
                        workload_name
                    ):
                        pass

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CoveragePlotGenerator(
    PlotGenerator,
    generator_name="coverage",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE]
):
    """Generates repo-churn plot(s) for the selected case study(ies)."""

    def generate(self) -> tp.List[Plot]:
        return [CoveragePlot(self.plot_config, **self.plot_kwargs)]


class WLCoverageReportAggregate(
    WorkloadSpecificReportAggregate[CoverageReport],
    shorthand=CoverageReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Aggregate CoverageReports."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, CoverageReport)

    def workload_names(self) -> tp.Collection[str]:
        return self.keys()

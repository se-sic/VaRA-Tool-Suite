"""Plot for visualizing perf stat metrics."""
import typing as tp

import click
import matplotlib.pyplot as plt

from varats.data.reports.perf_stat_report import PerfStatReportAggregate
from varats.experiments.vara.perf_stat import PerfStatExperiment
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.cli_util import make_cli_option
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class PerfStatPlot(Plot, plot_name='fperf_stat'):
    """Visualizes metrics collected with perf stat."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        for case_study in case_studies:
            report_files = get_processed_revisions_files(
                'PrimeNumbers',
                PerfStatExperiment,
                PerfStatReportAggregate,
                get_case_study_file_name_filter(case_study),
            )

            for report_filepath in report_files:
                agg_perfstat_report = PerfStatReportAggregate(
                    report_filepath.full_path()
                )

                reports = agg_perfstat_report.reports()
                for report in reports:
                    df = report.df

                    x = df.index
                    y = df[self.plot_kwargs["value"]]
                    plt.plot(x, y)

                    # Add a title and labels
                    plt.title("Plot")
                    plt.xlabel("time")
                    plt.ylabel(self.plot_kwargs["value"])

                    plt.xticks(rotation=90)


class PerfStatPlotGenerator(
    PlotGenerator,
    generator_name="fperf-stat",
    options=[
        make_cli_option(
            "--value",
            type=click.Choice([
                "task-clock", "context-switches", "cpu-migrations",
                "page-faults", "cycles", "instructions", "branches",
                "branch-misses"
            ]),
            required=True,
            help="File type for the plot."
        )
    ]
):
    """Generates overhead plot."""

    def generate(self) -> tp.List[Plot]:
        return [PerfStatPlot(self.plot_config, **self.plot_kwargs)]

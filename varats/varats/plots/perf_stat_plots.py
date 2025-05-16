"""Plot for visualizing perf stat metrics."""
import typing as tp

import click
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes

from varats.data.reports.perf_stat_report import PerfStatReportAggregate
from varats.experiment.workload_util import get_workload_label
from varats.experiments.vara.perf_stat import PerfStatExperiment, PerfStat
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import create_multi_case_study_choice
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


def _aggregate_data(case_study: CaseStudy) -> pd.DataFrame:
    """Aggregate data from perf stat reports."""
    report_files = get_processed_revisions_files(
        case_study.project_name,
        PerfStatExperiment,
        PerfStatReportAggregate,
        get_case_study_file_name_filter(case_study),
        only_newest=False
    )

    result = pd.DataFrame()
    for report_filepath in report_files:
        config_id = report_filepath.report_filename.config_id
        agg_perfstat_report = PerfStatReportAggregate(
            report_filepath.full_path()
        )
        reports = agg_perfstat_report.reports()

        for report in reports:
            workload_label = get_workload_label(report.path)

            df = report.df

            # Drop unnecessary columns
            df = df.drop(
                columns=[c for c in df.columns if c not in PerfStat.METRICS],
                axis=1
            )

            df.reset_index(inplace=True, names=["interval"])
            df["workload"] = workload_label
            df["config_id"] = config_id
            result = pd.concat([result, df], ignore_index=True)

    return result


class PerfStatComparisonPlot(Plot, plot_name='perf_stat_comparison'):

    @property
    def name(self) -> str:
        return f"{self.NAME}_{self.plot_kwargs['metric']}"

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["cs"]
        metric = self.plot_kwargs["metric"]

        df = _aggregate_data(case_study)

        workloads = set(df["workload"].unique()
                       ) - {"example", "aim-100-1-6-no-1"}
        configs = df["config_id"].unique()

        fig = plt.figure(figsize=(8 * len(workloads), 8 * len(configs)))
        splots = fig.subplots(
            len(configs), len(workloads), sharex="col", sharey="all"
        )

        for i, config in enumerate(configs):
            for j, workload in enumerate(workloads):
                ax: Axes = splots[i, j]

                # Set the title and y label for subplots in first row/column
                if i == 0:
                    ax.set_title(workload)

                if j == 0:
                    ax.set_ylabel(f"Config: {config}")

                # Filter the DataFrame for the current config and workload
                filtered_df = df[(df["config_id"] == config) &
                                 (df["workload"] == workload)]

                # Plot the data
                ax.scatter(
                    filtered_df["interval"],
                    filtered_df[metric],
                    label=workload
                )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return set()


class PerfStatComparisonPlotGenerator(
    PlotGenerator,
    generator_name="perf-stat-comparison",
    options=[
        make_cli_option(
            "--case_study",
            type=create_multi_case_study_choice(),
            required=True,
            help="Case studies to generate the plot for."
        )
    ]
):
    """Generates a comparison plot for perf stat metrics."""

    def generate(self) -> tp.List[Plot]:
        return [
            PerfStatComparisonPlot(
                self.plot_config, cs=cs, metric=m, **self.plot_kwargs
            ) for cs in self.plot_kwargs["case_study"] for m in PerfStat.METRICS
        ]


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

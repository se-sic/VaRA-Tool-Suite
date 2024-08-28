import typing as tp
from itertools import chain

import click
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.text import Text

from varats.data.databases.feature_perf_precision_database import (
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    load_precision_data,
    load_overhead_data,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash
from varats.revision.revisions import get_processed_revisions_files
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.data.reports.perf_stat_report import PerfStatReport, PerfStatReportAggregate
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.experiments.vara.perf_stat import PerfStat, PerfStatExperiment


class PerfStatPlot(Plot, plot_name='fperf_stat'):
    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        for case_study in case_studies:
            project_name = case_study.project_name


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

class PerfStatPlotGenerator(
    PlotGenerator, generator_name="fperf-stat", options=[make_cli_option(
        "--value",
        type=click.Choice(["msec", "context-switches", "cpu-migrations", "page-faults", "cycles",
       "instructions", "branches", "branch-misses"]),
        required=True,
        help="File type for the plot."
    )]
):
    """Generates overhead plot."""

    def generate(self) -> tp.List[Plot]:
        return [PerfStatPlot(self.plot_config, **self.plot_kwargs)]
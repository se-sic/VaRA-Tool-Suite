"""Example table that uses different workloads and visualizes the time it took
to run them."""
import typing as tp
import re

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import WLTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY, REQUIRE_MULTI_EXPERIMENT_TYPE
from varats.utils.git_util import FullCommitHash

starting_budget_command_regex = re.compile("RunTracedNaive([0-9]+)")


class CompareRuntimesBudgetPlot(Plot, plot_name="compare_runtimes_budget"):

    def plot(self, view_mode: bool) -> None:
        df = pd.DataFrame()

        for case_study in self.plot_kwargs["case_study"]:
            project_name = case_study.project_name

            experiments = self.plot_kwargs["experiment_type"]

            for experiment in experiments:
                report_files = get_processed_revisions_files(
                    project_name,
                    experiment,
                    WLTimeReportAggregate,
                    get_case_study_file_name_filter(case_study),
                    only_newest=False
                )

                if (
                    m :=
                    re.search(starting_budget_command_regex, experiment.NAME)
                ) is not None:
                    budget = int(m.group(1))
                elif experiment.NAME.startswith("RunTracedNaive"):
                    budget = 20
                else:
                    budget = 0

                for report_filepath in report_files:
                    agg_time_report = WLTimeReportAggregate(
                        report_filepath.full_path()
                    )

                    for workload_name in agg_time_report.workload_names():
                        for report in agg_time_report.reports(workload_name):

                            new_row = {
                                "Workload":
                                    workload_name,
                                "Budget":
                                    budget,
                                "Mean wall time (msecs)":
                                    report.wall_clock_time.total_seconds()
                            }

                            df = pd.concat([df, pd.DataFrame([new_row])],
                                           ignore_index=True)

        fig, ax = plt.subplots()
        fig.set_size_inches(11.7, 8.27)
        sns.barplot(
            x="Budget",
            y="Mean wall time (msecs)",
            estimator=np.mean,
            data=df,
            ax=ax,
        )
        sns.despine()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CompareRuntimesBudgetPlotCSGenerator(
    PlotGenerator,
    generator_name="compare-runtimes-budget",
    options=[REQUIRE_MULTI_EXPERIMENT_TYPE, REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        return [CompareRuntimesBudgetPlot(self.plot_config, **self.plot_kwargs)]

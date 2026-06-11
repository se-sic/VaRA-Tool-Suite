import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter

from varats.data.databases.hidden_configurability_database import (
    aggregate_data,
    filter_baseline_rows,
    filter_for_significant_changes,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import create_multi_case_study_choice
from varats.utils.git_util import FullCommitHash


class PerfChangeSummaryPlot(Plot, plot_name="hc-perf-change-summary"):
    """
    Box plot for performance changes.

    Plots all relative performance changes grouped by case study.
    """

    def calc_missing_revisions(self, boundary_gradient: float) \
            -> set[FullCommitHash]:
        pass

    def plot(self, view_mode) -> None:
        case_studies = self.plot_kwargs["case_studies"]

        # Build data for box plot
        # Concat all CS data into one dataframe, adding a project column for later grouping
        plot_data = pd.DataFrame()

        for cs in case_studies:
            if cs.project_name not in _PROJECT_WORKLOADS:
                print(
                    f"Skipping {cs.project_name} as it is not "
                    f"an active HV subject system"
                )
                continue
            print(f"Processing {cs.project_name}...")

            cs_data = aggregate_data(cs, None)
            if cs_data.empty:
                print(f"No data for {cs.project_name}, skipping.")
                continue
            # Exclude baseline rows
            cs_data = filter_baseline_rows(cs_data)

            # Only consider significant changes
            sig_data = filter_for_significant_changes(cs_data)

            # Calculate means for relative changes
            sig_data["value_relative"] = sig_data["value_relative"].apply(
                np.mean
            )

            # Add project column for grouping
            sig_data["project"] = cs.project_name

            # Append to plot data
            plot_data = pd.concat([plot_data, sig_data], ignore_index=True)

        # Create box plot
        sns.boxplot(x="project", y="value_relative", data=plot_data)

        # Add percent formatter to y-axis
        plt.gca().yaxis.set_major_formatter(
            PercentFormatter(decimals=0,xmax=1)
        )

        plt.title("Relative Performance Changes by Project")
        plt.ylabel("Relative Performance Change (%)")
        plt.xlabel("")
        plt.xticks(rotation=90)
        plt.tight_layout()

class PerfChangeSummaryPlotGenerator(PlotGenerator,
                                     generator_name="hc-perf-change-summary",
                                     options=[
                                    make_cli_option(
                                                "--case-studies",
                                                type=create_multi_case_study_choice(),
                                                required=False,
                                                help="Case study to plot",
                                            )
                                    ]):
    def generate(self) -> list[Plot]:
        if not self.plot_kwargs["case_studies"]:
            self.plot_kwargs["case_studies"] = get_loaded_paper_config().get_all_case_studies()
        return [PerfChangeSummaryPlot(self.plot_config,**self.plot_kwargs)]
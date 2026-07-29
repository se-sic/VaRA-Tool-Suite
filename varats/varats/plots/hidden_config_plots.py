import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.pyplot import plot_date
from matplotlib.ticker import PercentFormatter

from varats.data.databases.hidden_configurability_database import (
    aggregate_data_for_cs,
    filter_baseline_rows,
    filter_for_significant_changes, filter_significant_kruskal_wallis, group_kruskal_wallis,
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

def _load_data_for_case_studies(case_studies) -> pd.DataFrame:
    plot_data = pd.DataFrame()

    for cs in case_studies:
        if cs.project_name not in _PROJECT_WORKLOADS:
            print(
                f"Skipping {cs.project_name} as it is not "
                f"an active HV subject system"
            )
            continue
        print(f"Processing {cs.project_name}...")

        cs_data = aggregate_data_for_cs(cs, None)
        if cs_data.empty:
            print(f"No data for {cs.project_name}, skipping.")
            continue
        # Exclude baseline rows
        cs_data = filter_baseline_rows(cs_data)

        # Only consider significant changes
        sig_data = filter_for_significant_changes(cs_data)

        # Calculate means for relative changes
        sig_data["value_relative_mean"] = sig_data["value_relative"].apply(
            np.mean
        )

        # Add project column for grouping
        sig_data["project"] = cs.project_name

        # Append to plot data
        plot_data = pd.concat([plot_data, sig_data], ignore_index=True)

    return plot_data

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
        plot_data = _load_data_for_case_studies(case_studies)

        # Create box plot
        sns.boxplot(x="project", y="value_relative_mean", data=plot_data, color="orange")

        # light gray dashed horizontal line at y=0
        plt.axhline(y=0, color='lightgray', alpha=0.6, linestyle='--')

        # Add percent formatter to y-axis
        plt.gca().yaxis.set_major_formatter(
            PercentFormatter(decimals=0,xmax=1)
        )

        plt.title("")
        plt.ylabel("Relative Performance Change (%)")
        # Y-Label right side of the plot
        plt.gca().yaxis.set_label_position("right")
        # Y-ticks right side of the plot
        plt.gca().yaxis.tick_right()
        plt.xlabel("")
        plt.xticks()

        # Increase font size of ticks
        plt.xticks(fontsize=11.5)
        plt.yticks(fontsize=11.5)
        # Increase font size of y-label
        plt.gca().yaxis.label.set_size(14)
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

class PerfChangeInSettingPlot(Plot, plot_name="hc-setting-kw"):
    """
    Box plot for performance changes in a specific setting.

    Plots all relative performance changes grouped by case study.
    """
    @property
    def name(self) -> str:
        return f"{self.plot_kwargs['case_study'].project_name}_{self.plot_kwargs['group_by'].replace(',','-')}_hc-setting-kw"

    def calc_missing_revisions(self, boundary_gradient: float):
        pass

    def plot(self, view_mode) -> None:
        case_study = self.plot_kwargs["case_study"]
        group_by = self.plot_kwargs["group_by"].split(",")

        # Build data for box plot
        # Concat all CS data into one dataframe, adding a project column for later grouping
        setting_data = _load_data_for_case_studies([case_study])
        sig_data = group_kruskal_wallis(setting_data, group_by)
        sig_data = filter_significant_kruskal_wallis(sig_data)

        sig_data["means_delta"] = sig_data["max_value_relative_mean"] - sig_data["min_value_relative_mean"]

        limit_groups = self.plot_kwargs.get("limit_groups")

        if limit_groups and limit_groups < len(sig_data):
            # Uniformly select N groups that cover the whole range of deltas
            sig_data = sig_data.sort_values(by="means_delta")

            indices = [0]

            step_width = len(sig_data) // (limit_groups - 1)
            for i in range(1, limit_groups - 1):
                indices += [i * step_width]

            indices += [len(sig_data) - 1]

            sig_data = sig_data.iloc[indices]

        # Enlarge figure if there are many groups
        if len(sig_data) > 10:
            print(f"Enlarging figure for {case_study.project_name} with group_by {group_by} due to many groups ({len(sig_data)}).")
            plt.figure(figsize=(len(sig_data) * 0.8, 4.8))
        else:
            # Set plot size to be half as high as default, but keep width the same
            plt.figure(figsize=(6.4, 4.8 * 0.75))

        plot_rows = []
        # Create df for plot:
        for _, group in sig_data.iterrows():
            means = group["mean_values_relative"]
            for m in means:
                plot_rows.append({
                    "setting_id": group["id"],
                    "value_relative": m
                })

        plot_data = pd.DataFrame.from_records(plot_rows)

        if plot_data.empty:
            print(f"No significant changes for {case_study.project_name} with group_by {group_by}.")
            return

        plot_args = {}
        if self.plot_kwargs.get("color"):
            plot_args["color"] = self.plot_kwargs.get("color")


        sns.boxplot(x="setting_id", y="value_relative", data=plot_data, **plot_args)

        # Add percent formatter to y-axis
        plt.gca().yaxis.set_major_formatter(
            PercentFormatter(xmax=1)
        )

        plt.ylabel("Relative Performance Change (%)")
        plt.xlabel(self.plot_kwargs.get("xlabel", "Setting ID"))

        # Increase font size of ticks
        plt.xticks(fontsize=11.5)
        plt.yticks(fontsize=11.5)
        # Increase font size of y-label
        plt.gca().yaxis.label.set_size(12)
        plt.gca().xaxis.label.set_size(12)
        # Show no x-ticks if there are too many groups
        #plt.xticks([])
        plt.tight_layout()

class PerfChangeInSettingPlotGenerator(PlotGenerator,
                                     generator_name="hc-setting-kw",
                                     options=[
                                    make_cli_option(
                                                "--study",
                                                type=create_multi_case_study_choice(),
                                                required=True,
                                                help="Case study to plot",
                                            ),
                                         # DF columns to group by
                                         make_cli_option(
                                                "--group-by",
                                                type=str,
                                                required=False,
                                                help="Columns to group by for Kruskal-Wallis test",
                                                default="binary-wl,config_id,metric"
                                            ),
                                         # Color for the plot
                                         make_cli_option(
                                                "--color",
                                                type=str,
                                                required=False,
                                                help="Color for the plot",
                                         ),
                                         # Limit groups
                                         make_cli_option(
                                                "--limit-groups",
                                                type=int,
                                                required=False,
                                                help="Limit the number of groups to plot",
                                         ),
                                         # xlabel
                                        make_cli_option(
                                                "--xlabel",
                                                type=str,
                                                required=False,
                                                help="X-axis label for the plot",
                                        )
                                    ]):
    def generate(self) -> list[Plot]:
        # Ensure that limit_groups is at least 2
        if self.plot_kwargs.get("limit_groups") and self.plot_kwargs["limit_groups"] < 2:
            raise ValueError("limit_groups must be at least 2")
        return [PerfChangeInSettingPlot(self.plot_config,case_study=cs,**self.plot_kwargs) for cs in self.plot_kwargs["study"]]
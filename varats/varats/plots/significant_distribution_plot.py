import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from varats.data.databases.hidden_configurability_database import (
    aggregate_data,
    ACTIVE_HV_PROJECTS,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.ts_utils.cli_util import make_cli_option
from varats.utils.git_util import FullCommitHash


class SignificantAlternativesSharePlot(
    Plot, plot_name="hc_significant_alts_share_plot"
):
    """Plot the density of significant differences across all comparisons."""

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    @property
    def name(self) -> str:
        name = self.NAME
        if self.plot_kwargs["case_studies"]:
            name += f"_{self.plot_kwargs['case_studies']}"
        if self.plot_kwargs["metrics"]:
            name += f"_{self.plot_kwargs['metrics']}"
        if self.plot_kwargs["workload"]:
            name += f"_{self.plot_kwargs['workload']}"
        return name.replace("/", "+")

    def __dummy_data(self):
        table_rows = []
        for _ in range(1000):
            # Generate dummy data for the plot with random shares of significant differences
            new_row = {
                "project": "dummy_project",
                "metric": "dummy_metric",
                "wl": "dummy_workload",
                "co": "dummy_confopp",
                # Generate random value 0,1
                "share": np.random.rand(),
            }
            table_rows.append(new_row)

        return pd.DataFrame.from_records(table_rows)

    def load_data(self):
        case_studies = self.plot_kwargs.get("case_study", None)

        if not case_studies:
            case_studies = get_loaded_paper_config().get_all_case_studies()

        if self.plot_kwargs["case_studies"]:
            selected_case_studies = self.plot_kwargs["case_studies"].split(",")
            case_studies = [
                cs for cs in case_studies
                if cs.project_name in selected_case_studies
            ]

        table_rows = []

        for cs in case_studies:
            if cs.project_name not in ACTIVE_HV_PROJECTS:
                print(
                    f"Skipping {cs.project_name} as it is not an active HV subject system"
                )
                continue
            print(f"Processing {cs.project_name}...")
            # Filter to single config ID for projects with multiple
            __cs_configs = {
                "libzmq": [13],
                "FastDownward": [0],
                "libvpx": [0],
            }
            if cs.project_name in __cs_configs:
                config_id = __cs_configs[cs.project_name][0]
            else:
                config_id = None
            try:
                cs_df = aggregate_data(cs, [config_id])
            except Exception as e:
                print(f"Error processing {cs.project_name}: {e}")
                continue

            cs_df = cs_df[cs_df["config_opportunity"] != "__baseline__"]

            # Filter based on selected workloads and metrics
            if self.plot_kwargs["workload"]:
                selected_workloads = self.plot_kwargs["workload"].split(",")
                cs_df = cs_df[cs_df["binary-wl"].apply(
                    lambda x: any(wl in x for wl in selected_workloads)
                )]

            if self.plot_kwargs["metrics"]:
                selected_metrics = self.plot_kwargs["metrics"].split(",")
                cs_df = cs_df[cs_df["metric"].isin(selected_metrics)]

            cs_df["significant"] = cs_df["significance"].apply(
                lambda x: 1 if x.pvalue < 0.05 else 0
            )

            # The same opportunity occurs multiple times (with the same variations) for multiple combinations of binary and workload.
            # We want separate rows/statistics for each workload/metric combination, so we group by these and the configuration opportunity and calculate the share of significant differences for each group.
            cs_df = cs_df.groupby(["binary-wl", "metric",
                                   "config_opportunity"]).agg(
                                       total_variations=pd.NamedAgg(
                                           column="variation", aggfunc="count"
                                       ),
                                       significant_variations=pd.NamedAgg(
                                           column="significant", aggfunc="sum"
                                       )
                                   ).reset_index()

            # Convert to table rows
            cs_df["share"
                 ] = cs_df["significant_variations"] / cs_df["total_variations"]
            cs_df["project"] = cs.project_name

            table_rows.extend(
                cs_df[[
                    "project", "binary-wl", "metric", "config_opportunity",
                    "share"
                ]].to_dict("records")
            )

        return pd.DataFrame.from_records(table_rows)

    def plot(self, view_mode: bool) -> None:
        # Load the data
        data = self.load_data()

        if data.empty:
            print("No data to plot.")
            return

        # Calculate the density of significant differences
        plt.figure(figsize=(10, 6))
        if True:
            # test histogram as alternative to density plot, bins each 5%
            bins = 20
            bin_width = 0.05

            sns.histplot(data['share'], bins=20, kde=False)
        else:
            sns.kdeplot(data['share'], fill=True, clip=(0, 1), bw_adjust=0.2)
            plt.title('Density of Significant Differences')
            plt.xlabel(
                'Share of configuration alternatives with significant difference to baseline'
            )
            plt.ylabel('Density')

        plt.xlabel(
            'Share of configuration alternatives with significant difference to baseline'
        )
        plt.xticks([0.05 * i + 0.025 for i in range(bins)], ["< 5%"] +
                   [f"{5*i}-{5*(i+1)}%" for i in range(1, bins - 1)] +
                   ["> 95%"])
        # Rotate xticks for better readability
        plt.xticks(rotation=90)


class SignificantAlternativesSharePlotGenerator(
    PlotGenerator,
    generator_name="hc_significant_alts_share",
    options=[
        make_cli_option(
            "--metrics",
            help=
            "Comma-separated list of metrics to include in the plot. If not specified, all metrics are included.",
            type=str,
            default=None
        ),
        make_cli_option(
            "--case-studies",
            help=
            "Comma-separated list of case studies to include in the plot. If not specified, all case studies are included.",
            type=str,
            default=None
        ),
        make_cli_option(
            "--workload",
            help=
            "Comma-separated list of workloads to include in the plot. If not specified, all workloads are included.",
            type=str,
            default=None
        )
    ]
):
    """Generator for SignificantAlternativesSharePlot."""

    def generate(self) -> tp.List[Plot]:
        return [
            SignificantAlternativesSharePlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class GenerateAllSharesPlot(
    PlotGenerator, generator_name="hc_all_significant_alts_shares", options=[]
):

    def generate(self) -> tp.List['varats.plot.plot.Plot']:
        all_cs = get_loaded_paper_config().get_all_case_studies()
        plots = []
        for cs in all_cs:
            __cs_configs = {
                "libzmq": [13],
                "FastDownward": [0],
                "libvpx": [0],
            }
            if cs.project_name in __cs_configs:
                config_id = __cs_configs[cs.project_name][0]
            else:
                config_id = None
            try:
                cs_df = aggregate_data(cs, [config_id])
            except Exception as e:
                print(f"Error processing {cs.project_name}: {e}")
                continue

            workloads = cs_df["binary-wl"].unique()
            metrics = cs_df["metric"].unique()

            plots += [
                SignificantAlternativesSharePlot(
                    self.plot_config,
                    **self.plot_kwargs,
                    case_studies=cs.project_name,
                    workload=w,
                    metrics=m
                ) for w in workloads for m in metrics
            ]

        return plots

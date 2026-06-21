import typing as tp

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter

from varats.data.cache_helper import cache_dataframe, load_cached_df_or_none
from varats.data.databases.hidden_configurability_database import (
    aggregate_data_for_cs,
    filter_baseline_rows,
)
from varats.experiments.vara.hidden_configurability_experiments import (
    _PROJECT_WORKLOADS,
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

    @staticmethod
    def _load_cached_data():
        dtypes = {
            "project": "str",
            "binary-wl": "str",
            "metric": "str",
            "config_opportunity": "str",
            "share": "float"
        }
        df = load_cached_df_or_none(
            "HC-SIG-PLOT", "ALL", dtypes
        )

        if df is None:
            return None

        return df

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

        cached_df = self._load_cached_data()
        if cached_df is not None:
            print("Using cached data for significant alternatives share plot.")
            return cached_df

        for cs in case_studies:
            if cs.project_name not in _PROJECT_WORKLOADS:
                print(
                    f"Skipping {cs.project_name} as it is not "
                    f"an active HV subject system"
                )
                continue
            cs_df = aggregate_data_for_cs(cs, None)
            if cs_df.empty:
                print(f"No data for {cs.project_name}, skipping.")
                continue

            cs_df = filter_baseline_rows(cs_df)

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

        df = pd.DataFrame.from_records(table_rows)

        # Cache DF
        cache_dataframe("HC-SIG-PLOT", "ALL", df)

        return df

    def plot(self, view_mode: bool) -> None:
        # Load the data
        data = self.load_data()

        if data.empty:
            print("No data to plot.")
            return

        # Multiple violin plots
        # We want one overall violin plot with a left half violin
        # Then for each domain we want a separate right half violin plot, all on the same axis
        # We can achieve this by preparing the data in the right way
        #   - Add a column "domain" to the data, which contains the domain of the project
        #   - Duplicate each row with a domain "all" for the overall density plot
        #   - Include a side column that is either "left" for the overall plot or "right" for the domain plots
        # We then use violinplot with x="domain", y="share", hue="side"
            # Add group column for multiple plots
        domain_mapping = {
            project.project_cls.NAME: str(project.project_cls.DOMAIN)
            for project in get_loaded_paper_config().get_all_case_studies()}
        data["domain"] = data["project"].apply(lambda x: domain_mapping.get(x, "other"))
        data["side"] = "right"

        # Add one dummy entry per domain for the right side
        for domain in data["domain"].unique():
            dummy_row = {
                "project": "dummy_project",
                "binary-wl": "dummy_binary_wl",
                "metric": "dummy_metric",
                "config_opportunity": "dummy_config_opportunity",
                "share": 0,
                "domain": domain,
                "side": "left"
            }
            data = pd.concat([data, pd.DataFrame.from_records([dummy_row])], ignore_index=True)

        all_data = data.copy()
        all_data["domain"] = "All"
        all_data["side"] = "left"

        vals = all_data["share"].values

        q1, q2, q3 = np.percentile(vals, [25, 50, 75])

        data = pd.concat([data, all_data], ignore_index=True)

        dummy_row = {
            "project": "dummy_project",
            "binary-wl": "dummy_binary_wl",
            "metric": "dummy_metric",
            "config_opportunity": "dummy_config_opportunity",
            "share": 0,
            "domain": "All",
            "side": "right"
        }
        data = pd.concat([data, pd.DataFrame.from_records([dummy_row])], ignore_index=True)

        # Set figure width based on number of domains
        plt.figure(figsize=(len(data["domain"].unique()) * 2, 4))

        ax = sns.violinplot(data=data,
                       x="domain",
                       y="share",
                       hue="side",
                       split=True,
                       inner="quart",
                       bw_method=0.2,
                       order=sorted(data["domain"].unique().tolist()),
                       hue_order=["left", "right"],
                       width=0.8,
                       dodge=False)

        for q in [q1, q3]:
            ax.axhline(
                q,
                color="red",
                linestyle=":",
                alpha=0.5,
                zorder=0
            )
        ax.axhline(
            q2,
            color="red",
            linestyle="--",
            alpha=0.5,
            zorder=0
        )

        # Hide legend
        plt.legend([], [], frameon=False)
        # Cut off y at 0,1
        plt.ylim(0, 1)
        plt.ylabel("")
        plt.xlabel("")

        # Percent formatter for y axis
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))


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

    def generate(self) -> list[Plot]:
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
                cs_df = aggregate_data_for_cs(cs, [config_id])
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

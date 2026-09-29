"""Module for plotting distributions of HC Data."""

from enum import Enum

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
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class SignificantAlternativesSharePlot(
    Plot, plot_name="hc_significant_alts_share_plot"
):
    """Plot the density of significant differences across all comparisons."""

    def calc_missing_revisions(
        self,
        boundary_gradient: float,  # noqa: ARG002
    ) -> set[FullCommitHash]:
        """Unsupported."""
        raise UnsupportedOperation()

    @property
    def name(self) -> str:
        """Generates the name based on arguments."""
        name = self.NAME
        if self.plot_kwargs["case_studies"]:
            name += f"_{self.plot_kwargs['case_studies']}"
        if self.plot_kwargs["metrics"]:
            name += f"_{self.plot_kwargs['metrics']}"
        if self.plot_kwargs["workload"]:
            name += f"_{self.plot_kwargs['workload']}"
        return name.replace("/", "+")

    @staticmethod
    def __dummy_data():
        table_rows = []
        for _ in range(1000):
            # Generate dummy data with random shares of significant differences
            new_row = {
                "project": "dummy_project",
                "metric": "dummy_metric",
                "wl": "dummy_workload",
                "co": "dummy_confopp",
                # Generate random value 0,1
                "share": np.random.default_rng().uniform(0, 1),
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
            "share": "float",
        }
        df = load_cached_df_or_none("HC-SIG-PLOT", "ALL", dtypes)

        if df is None:
            return None

        return df

    def load_data(self):
        """Load the data for the plot."""
        case_studies = self.plot_kwargs.get("case_study", None)

        if not case_studies:
            case_studies = get_loaded_paper_config().get_all_case_studies()

        if self.plot_kwargs["case_studies"]:
            selected_case_studies = self.plot_kwargs["case_studies"].split(",")
            case_studies = [
                cs
                for cs in case_studies
                if cs.project_name in selected_case_studies
            ]

        table_rows = []

        if (cached_df := self._load_cached_data()) is not None:
            print("Using cached data for significant alternatives share plot.")
            return cached_df

        for cs in case_studies:
            print(f"Processing {cs.project_name}")
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
                cs_df = cs_df[
                    cs_df["binary-wl"].apply(
                        lambda x: any(wl in x for wl in selected_workloads)
                    )
                ]

            if self.plot_kwargs["metrics"]:
                selected_metrics = self.plot_kwargs["metrics"].split(",")
                cs_df = cs_df[cs_df["metric"].isin(selected_metrics)]

            cs_df["significant"] = cs_df["significance"].apply(
                lambda x: 1 if x.pvalue < 0.05 else 0
            )

            # The same opportunity occurs multiple times (with the same
            # variations) for multiple combinations of binary and workload.
            # We want separate rows/statistics for each workload/metric
            # combination, so we group by these and the configuration
            # opportunity and calculate the share of significant
            # differences for each group.
            cs_df = (
                cs_df.groupby(["binary-wl", "metric", "config_opportunity"])
                .agg(
                    total_variations=pd.NamedAgg(
                        column="variation", aggfunc="count"
                    ),
                    significant_variations=pd.NamedAgg(
                        column="significant", aggfunc="sum"
                    ),
                )
                .reset_index()
            )

            # Convert to table rows
            cs_df["share"] = (
                cs_df["significant_variations"] / cs_df["total_variations"]
            )
            cs_df["project"] = cs.project_name

            table_rows.extend(
                cs_df[
                    [
                        "project",
                        "binary-wl",
                        "metric",
                        "config_opportunity",
                        "share",
                    ]
                ].to_dict("records")
            )

        df = pd.DataFrame.from_records(table_rows)

        # Cache DF
        cache_dataframe("HC-SIG-PLOT", "ALL", df)

        return df

    def _add_axis_formatting(self, ax: plt.Axes) -> None:

        # Hide legend
        plt.legend([], [], frameon=False)
        # Cut off y at 0,1
        plt.xlim(0, 1)
        plt.ylabel("")
        plt.xlabel("")

        # Percent formatter for y axis
        plt.gca().xaxis.set_major_formatter(PercentFormatter(1.0))

        # Move y-axis to the right
        plt.gca().yaxis.set_label_position("right")
        plt.gca().yaxis.tick_right()

        # Remove ticks for y-axis,
        # Instead draw the domain name in the middle of the violin plot
        # tick_names = [item.get_text() for item in ax.get_yticklabels()]
        # ax.set_yticklabels([])
        # for i, tick_name in enumerate(tick_names):
        #    ax.text(
        #        0.5,
        #        i+0.525,
        #        tick_name,
        #        transform=ax.get_yaxis_transform(),
        #        ha="center",
        #        va="center",
        #        fontsize=6
        #    )

        # remove y-ticks
        # ax.tick_params(axis='y', which='both', length=0)

        # Extend y-axis of plt to the bottom to make space for domain label
        # ax.margins(y=0.025)
        # Change font size of y-ticks
        ax.tick_params(axis='y', labelsize=5, which='both', length=0)
        # Rotate y-tick labels by 90 degrees and on the right side of the axis
        ax.set_yticklabels(ax.get_yticklabels(), rotation=90, va="center")
        # Move closer to the axis
        ax.yaxis.set_tick_params(pad=2)

        # Change font size of x-ticks
        ax.tick_params(axis='x', labelsize=6)

    @staticmethod
    def _add_quartile_lines(
        ax: plt.Axes, q1: float, q2: float, q3: float
    ) -> None:
        for q in [q1, q3]:
            ax.axvline(
                q, color="red", linestyle=":", alpha=0.5, zorder=0, lw=0.75
            )
        ax.axvline(
            q2, color="red", linestyle="--", alpha=0.5, zorder=0, lw=0.75
        )

        # Add labels for the quartiles
        # Add them on the left side of the axis, centered on the quartile lines,
        # with a small offset to the left
        for q, label in zip(
            [q1, q2, q3], ["Q1 (All)", "Median (All)", "Q3 (All)"]
        ):
            plt.text(
                q,
                -0.55,
                label,
                color="red",
                fontsize=5,
                ha="center",
                va="bottom",
                alpha=0.5,
            )

    def _plot_violin_vstack(self) -> None:
        # Load the data
        data = self.load_data()

        if data.empty:
            print("No data to plot.")
            return

        domain_mapping = {
            project.project_cls.NAME: str(project.project_cls.DOMAIN)
            for project in get_loaded_paper_config().get_all_case_studies()
        }
        data["domain"] = data["project"].apply(
            lambda x: domain_mapping.get(x, "other")
        )

        def _add_dummy_row(df, domain: str, side: str) -> pd.DataFrame:
            dummy_row = {
                "project": "dummy_project",
                "binary-wl": "dummy_binary_wl",
                "metric": "dummy_metric",
                "config_opportunity": "dummy_config_opportunity",
                "share": -1,
                "domain": domain,
                "side": side,
            }
            return pd.concat(
                [df, pd.DataFrame.from_records([dummy_row])], ignore_index=True
            )

        # Multiple violin plots
        # We want one overall violin plot with a left half violin
        # Then for each domain we want a separate right half-violin plot
        # all on the same axis
        # We can achieve this by preparing the data in the right way
        #   - Add a column "domain", which contains the project domain
        #   - Duplicate each row with domain "all" for the overall density plot
        #   - Include a side column that is either "left" for the overall plot
        #     or "right" for the domain plots
        # We then use violinplot with x="domain", y="share", hue="side"
        # Add group column for multiple plots
        data["side"] = "right2"

        # Add one dummy entry per domain for the right side
        for domain in data["domain"].unique():
            data = _add_dummy_row(data, domain, "left1")
            data = _add_dummy_row(data, domain, "left2")

        all_data = data.copy()
        all_data["domain"] = "All"
        all_data["side"] = "right1"

        vals = all_data["share"].to_numpy()

        q1, q2, q3 = np.percentile(vals, [25, 50, 75])

        data = pd.concat([data, all_data], ignore_index=True)

        data = _add_dummy_row(data, "All", "right2")
        data = _add_dummy_row(data, "All", "left1")
        data = _add_dummy_row(data, "All", "left2")

        # Set figure width based on number of domains
        plt.figure(figsize=(5, len(data["domain"].unique()) * 1.2))

        ax = sns.violinplot(
            data=data,
            x="share",
            y="domain",
            hue="side",
            split=True,
            inner="quart",
            bw_method=0.2,
            order=sorted(data["domain"].unique().tolist()),
            hue_order=["right1", "left1", "right2", "left2"],
            palette={
                "left1": "lightgray",
                "right1": sns.color_palette()[0],
                "left2": "lightgray",
                "right2": sns.color_palette()[1],
            },
            width=0.9,
            dodge=False,
            density_norm="width",
            orient="h",
        )

        self._add_quartile_lines(ax, q1, q2, q3)
        self._add_axis_formatting(ax)

    def _plot_sven(self):
        # Load the data
        data = self.load_data()

        if data.empty:
            print("No data to plot.")
            return

        domain_mapping = {
            project.project_cls.NAME: str(project.project_cls.DOMAIN)
            for project in get_loaded_paper_config().get_all_case_studies()
        }
        data["domain"] = data["project"].apply(
            lambda x: domain_mapping.get(x, "other")
        )

        all_data = data.copy()
        all_data["domain"] = "All"

        class Variant(Enum):
            SingleColumn = 1
            DoubleColumn = 2
            Funky = 3

        variant = Variant(3)

        match variant:
            case Variant.DoubleColumn:
                fig = plt.figure(figsize=(10, 2))
                # Variant B: Double-column mode. All domains as 2x2 on the left,
                # then three domains per row on the right
                grid_spec = fig.add_gridspec(nrows=2, ncols=5)
                all_axis = fig.add_subplot(grid_spec[0:2, 0:2])
                domain_axes = [
                    fig.add_subplot(grid_spec[i // 3, 2 + (i % 3)])
                    for i in range(len(data["domain"].unique()))
                ]
            case Variant.Funky:
                # A bit of a funky grid:
                #
                # A  A  A  D1
                # A  A  A  D2
                # D3 D4 D5 D6
                #
                # Where A is the all domains plot and D1-D6 are the domain plots
                fig = plt.figure(figsize=(8, 4.5))

                grid_spec = fig.add_gridspec(nrows=3, ncols=4, wspace=0.2)
                all_axis = fig.add_subplot(grid_spec[0:2, 0:3])

                domain_axes = [
                    fig.add_subplot(grid_spec[0, 3]),
                    fig.add_subplot(grid_spec[1, 3]),
                    fig.add_subplot(grid_spec[2, 0]),
                    fig.add_subplot(grid_spec[2, 1]),
                    fig.add_subplot(grid_spec[2, 2]),
                    fig.add_subplot(grid_spec[2, 3]),
                ]
            case Variant.SingleColumn:
                fig = plt.figure()
                # Variant A: All at top, then three projects per row
                grid_spec = fig.add_gridspec(nrows=3, ncols=3)
                all_axis = fig.add_subplot(grid_spec[0, :])
                domain_axes = [
                    fig.add_subplot(grid_spec[1 + (i // 3), i % 3])
                    for i in range(len(data["domain"].unique()))
                ]

        def _format_axis(ax: plt.Axes) -> None:
            # Hide legend
            ax.legend([], [], frameon=False)
            # Cut off x at 0,1
            ax.set_xlim(0, 1)
            ax.set_ylabel("")
            ax.set_xlabel("")

            # Percent formatter for y axis
            ax.xaxis.set_major_formatter(PercentFormatter(1.0))
            # Move xticks closer to the axis
            ax.xaxis.set_tick_params(pad=2)

            # Format xticks
            ax.tick_params(axis='x', labelsize=8)
            ax.tick_params(axis='y', which='both', length=0)

        sns.violinplot(
            data=data,
            x="share",
            split=True,
            inner="quart",
            bw_adjust=0.25,
            bw_method="silverman",
            width=0.9,
            dodge=False,
            orient="h",
            ax=all_axis,
        )

        all_axis.set_title("All Domains", fontsize=16, y=1.0, pad=-18)

        _format_axis(all_axis)

        for i, domain in enumerate(data["domain"].unique()):
            domain_axis = domain_axes[i]

            sns.violinplot(
                data=data[data["domain"] == domain],
                x="share",
                split=True,
                inner="quart",
                bw_adjust=0.25,
                bw_method="silverman",
                width=0.9,
                dodge=False,
                density_norm="area",
                orient="h",
                ax=domain_axis,
                color=sns.color_palette()[1],
            )
            _format_axis(domain_axis)

            domain_axis.set_title(domain, fontsize=11, y=1.0, pad=-13)

    def plot(self, view_mode: bool) -> None:  # noqa: ARG002
        """Plot the data."""
        self._plot_sven()


class SignificantAlternativesSharePlotGenerator(
    PlotGenerator,
    generator_name="hc_significant_alts_share",
    options=[
        make_cli_option(
            "--metrics",
            help="Comma-separated list of metrics to include in the plot."
            " If not specified, all metrics are included.",
            type=str,
            default=None,
        ),
        make_cli_option(
            "--case-studies",
            help="Comma-separated list of case studies to include in the plot."
            " If not specified, all case studies are included.",
            type=str,
            default=None,
        ),
        make_cli_option(
            "--workload",
            help="Comma-separated list of workloads to include in the plot."
            " If not specified, all workloads are included.",
            type=str,
            default=None,
        ),
    ],
):
    """Generator for SignificantAlternativesSharePlot."""

    def generate(self) -> list[Plot]:
        """Generate the plot."""
        return [
            SignificantAlternativesSharePlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class GenerateAllSharesPlot(
    PlotGenerator, generator_name="hc_all_significant_alts_shares", options=[]
):
    """Creates the plots for all case studies, workloads, and metrics."""

    def generate(self) -> list[Plot]:
        """Generate the plot."""
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

            cs_df = aggregate_data_for_cs(cs, [config_id])

            workloads = cs_df["binary-wl"].unique()
            metrics = cs_df["metric"].unique()

            plots += [
                SignificantAlternativesSharePlot(
                    self.plot_config,
                    **self.plot_kwargs,
                    case_studies=cs.project_name,
                    workload=w,
                    metrics=m,
                )
                for w in workloads
                for m in metrics
            ]

        return plots

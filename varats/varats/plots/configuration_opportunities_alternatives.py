import typing as tp
from itertools import product

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import SubFigure
from matplotlib.ticker import PercentFormatter

from varats.data.databases.hidden_configurability_database import (
    aggregate_data,
    get_data_for_single_config,
    get_configuration_points,
    extract_config_point,
    add_significance_values,
)
from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.vara.hidden_configurability_experiments import (
    TimePatchedWorkloads,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import TimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import create_multi_case_study_choice
from varats.utils.git_util import FullCommitHash


class SignificantOpportunitiesDistPlot(
    Plot, plot_name="significant_opportunities_dist"
):

    @property
    def name(self) -> str:
        return f"{self.NAME}_{self.plot_kwargs['metric']}"

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        metric: str = self.plot_kwargs["metric"]
        print(f"Plotting case study {case_study.project_name} with {metric}")

        full_data = aggregate_data(case_study, None)

        if full_data.empty:
            print(f"No data for {case_study.project_name}")
            return

        # Select metric and filter out baseline data
        metric_df = full_data[
            (full_data["metric"] == metric) &
            (full_data["config_opportunity"] != "__baseline__")]

        sig_df = metric_df[
            metric_df.apply(lambda x: x["significance"].pvalue < 0.05, axis=1)]
        sig_df = sig_df.explode("value_relative", ignore_index=True)

        extra_args = {}

        if self.plot_kwargs["explode"]:
            extra_args = {
                "hue": "config_opportunity",
                "col": "config_id",
                "col_wrap": 5,
            }

        g = sns.displot(sig_df, x="value_relative", kind="kde", **extra_args)

        for ax in g.axes.flat:
            ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0))
            ax.tick_params(labelbottom=True)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return set()


class SignificantOpportunitiesDistGenerator(
    PlotGenerator,
    generator_name="significant_opportunities_dist",
    options=[
        make_cli_option(
            "--case-studies",
            type=create_multi_case_study_choice(),
            required=True,
            help="Case studies to plot",
        ),
        make_cli_option(
            "--explode",
            is_flag=True,
            default=False,
            help=
            "Explodes the plot into multiple subplots for each config_id and configuration opportunity",
        ),
        make_cli_option(
            "--metrics",
            type=str,
            required=True,
            help="Metric to plot (e.g. wall_clock_time,max_resident_size)",
        ),
    ]
):

    def generate(self) -> tp.List[Plot]:
        return [
            SignificantOpportunitiesDistPlot(
                self.plot_config,
                case_study=cs,
                metric=metric,
                **self.plot_kwargs
            )
            for cs in self.plot_kwargs["case_studies"]
            for metric in self.plot_kwargs["metrics"].split(",")
        ]


class ConfigurationAlternativesAggPlot(
    Plot, plot_name="configuration_opportunities_alternatives_agg"
):
    """Plot that provides a concise overview of configuration alternatives for
    all configurations, workloads and binaries."""

    @property
    def name(self) -> str:
        return f"{self.NAME}_{self.plot_kwargs['metric']}"

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return set()

    def __create_palettes(
        self, df: pd.DataFrame
    ) -> tp.Dict[str, tp.Tuple[float, float, float]]:
        # Create a color palette for the variations
        configs = df['config_opportunity'].unique()

        # Generate base colors for each config_opportunity
        base_palette = sns.color_palette("Set2", n_colors=len(configs))
        config_to_basecolor = dict(zip(configs, base_palette))

        # Generate variation-level palette
        variation_palette = {}
        for config in configs:
            variations = df[df['config_opportunity'] == config
                           ]['variation'].unique()
            base = to_rgba(config_to_basecolor[config])
            num_variations = len(variations)

            # Set alpha values to stay within the range [0.6, 1.0], based on the number of variations
            for i, var in enumerate(variations):
                alpha = 1 - (
                    i / num_variations
                ) * 0.4  # Ensure alpha is in the range [0.6, 1.0]
                variation_palette[
                    (config, var)
                ] = base[:3] + (alpha,)  # Modify alpha but keep RGB part

        return variation_palette

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        metric: str = self.plot_kwargs["metric"]

        if "config_ids" in self.plot_kwargs:
            configs = [
                int(i) for i in self.plot_kwargs["config_ids"].split(",")
            ] if self.plot_kwargs["config_ids"] else [None]
        else:
            configs = case_study.get_config_ids_for_revision(
                case_study.revisions[0]
            )

        if len(configs) == 0:
            configs = [None]

        # Load data for first config to get the number of binaries
        df = get_data_for_single_config(case_study, configs[0])

        if df.empty:
            print(f"No data for {case_study.project_name} ({configs[0]})")
            return

        binaries = df["binary-wl"].unique()

        fig = plt.figure(figsize=(8 * len(configs), 8 * len(binaries)))
        sfigs = fig.subfigures(
            ncols=len(configs), nrows=len(binaries), squeeze=False
        )

        for conf_idx, config_id in enumerate(configs):
            print(f"Loading data for {case_study.project_name} ({config_id=})")
            # Load data for this config
            df = get_data_for_single_config(case_study, config_id)

            metric_palette = self.__create_palettes(df[df["metric"] == metric])

            #df["value"] = df["value"].apply(np.mean)
            df = df.explode("value")

            df["config_var"] = list(
                zip(df['config_opportunity'], df['variation'])
            )

            for bin_idx, binary in enumerate(binaries):
                print(f"Processing {binary} ({config_id=})")

                baseline_df = df[(df["binary-wl"] == binary) &
                                 (df["config_opportunity"] == "__baseline__")]

                binary_df = df[(df["binary-wl"] == binary) &
                               (df["config_opportunity"] != "__baseline__")]

                metric_df = binary_df[binary_df["metric"] == metric]

                subfig: SubFigure = sfigs[bin_idx, conf_idx]

                abs_ax, rel_ax = subfig.subplots(1, 2)

                abs_ax.set_title(f"{metric} (Absolute)")
                rel_ax.set_title(f"{metric} (Relative)")

                # Set the titles for first col/row
                if conf_idx == 0:
                    subfig.supylabel(
                        f"{binary}", size="xx-large", weight="bold"
                    )

                if bin_idx == 0:
                    subfig.suptitle(
                        f"Config ID: {config_id}",
                        size="x-large",
                        weight="bold"
                    )

                # Create strip plot for absolute values
                sns.stripplot(
                    ax=abs_ax,
                    y="value",
                    x="config_opportunity",
                    hue="config_var",
                    data=metric_df,
                    palette=metric_palette,
                )

                # Draw the baseline line for absolute plots
                abs_ax.axhline(
                    y=np.mean(
                        baseline_df[baseline_df["metric"] == metric]["value"]
                    ),
                    color='red',
                    linestyle='--',
                    linewidth=1,
                    label="Baseline"
                )

                # Create strip plot for relative change below
                sns.stripplot(
                    ax=rel_ax,
                    y="value_relative",
                    x="config_opportunity",
                    hue="config_var",
                    data=metric_df,
                    palette=metric_palette,
                )

                # Draw the baseline line for relative plots
                rel_ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
                rel_ax.set_ylim(-0.5, 0.5)
                rel_ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
                rel_ax.yaxis.tick_right()

                # Format the axes, labels, and legends

                for ax in (abs_ax, rel_ax):
                    ax.legend().remove()
                    ax.set_ylabel("")
                    ax.set_xlabel("")

                    if bin_idx == len(binaries) - 1:
                        ax.set_xticklabels(
                            ax.get_xticklabels(), rotation=90, ha='right'
                        )
                    else:
                        ax.set_xticklabels([])


class ConfigurationAlternativesAggGenerator(
    PlotGenerator,
    generator_name="co-alt-agg",
    options=[
        make_cli_option(
            "--case_studies",
            type=create_multi_case_study_choice(),
            required=True,
            help="Case studies to plot",
        ),
        make_cli_option(
            "--config_ids",
            type=str,
            required=False,
            help="Configuration IDs to plot",
        ),
        make_cli_option(
            "--metrics",
            # Type should be a comma-separated list of metrics
            type=str,
            required=True,
            help="Metrics to plot (e.g. wall_clock_time,max_resident_size)",
        )
    ]
):
    """Generates the configuration opportunities runtime plot."""

    def generate(self) -> tp.List[Plot]:
        return [
            ConfigurationAlternativesAggPlot(
                self.plot_config,
                case_study=cs,
                metric=metric,
                **self.plot_kwargs
            )
            for cs in self.plot_kwargs["case_studies"]
            for metric in self.plot_kwargs["metrics"].split(",")
        ]


class ConfigurationOpportunitiesRuntimePlot(
    Plot, plot_name="configuration_opportunities_variation"
):
    """Plot that compares base runtimes for configuration opportunities with
    alternative values."""

    def plot(self, view_mode: bool) -> None:
        df = self.tabulate()

        if df.empty:
            return

        sns.stripplot(
            df, y="performance", x="config_opportunity", hue="variation"
        )

        baseline_performance = df[df["variation"] == "baseline"
                                 ]["performance"].mean()
        plt.axhline(
            y=baseline_performance,
            color='red',
            linestyle='--',
            linewidth=1,
            label="Baseline"
        )
        plt.legend().remove()
        plt.xticks(rotation=90)
        plt.ylabel("Runtime (s)")

    def tabulate(self) -> pd.DataFrame:
        case_study: CaseStudy = self.plot_kwargs['case_study']

        result_files = get_processed_revisions_files(
            case_study.project_name, TimePatchedWorkloads,
            TimePatchedWorkloads.report_spec().main_report,
            get_case_study_file_name_filter(case_study)
        )

        if len(result_files) == 0:
            print(f"No results found for {case_study.project_name}")
            return pd.DataFrame()

        # TODO: Properly handle multiple binaries/configurations
        if len(result_files) > 1:
            print(f"More than one result for {case_study.project_name}")

        report: MPRTimeWLAggregate = MPRTimeWLAggregate(
            result_files[0].full_path()
        )

        configuration_points = get_configuration_points(report)

        base_report: TimeReportAggregate = report.get_baseline_report()

        df: pd.DataFrame = pd.DataFrame()

        #TODO: Handle different workloads
        base_runtime = base_report.measurements_wall_clock_time

        table_rows = []

        for cp in configuration_points:
            table_rows.append({
                "config_opportunity": cp,
                "variation": "baseline",
                "performance": base_runtime
            })

        for patch_report in report.get_patched_reports():
            cp = extract_config_point(patch_report.filename.filename)
            table_rows.append({
                "config_opportunity": cp[0],
                "variation": cp[1],
                "performance": patch_report.measurements_wall_clock_time
            })

        df = pd.DataFrame.from_records(table_rows)
        df = df.explode('performance')

        return df


class ConfigurationOpportunitiesRuntimeGenerator(
    PlotGenerator,
    generator_name="configuration-opportunities-variation",
    options=[]
):
    """Generates the configuration opportunities runtime plot."""

    def generate(self) -> tp.List[Plot]:
        return [
            ConfigurationOpportunitiesRuntimePlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in get_loaded_paper_config().get_all_case_studies()
        ]


class MinMaxAlternativesPlot(Plot, plot_name="min_max_alternatives"):

    @property
    def name(self) -> str:
        """Returns the name of the plot."""
        if self.plot_kwargs["significant_only"]:
            return f"{self.NAME}_{self.plot_kwargs['metric']}_significant"
        return f"{self.NAME}_{self.plot_kwargs['metric']}"

    def plot(self, view_mode: bool) -> None:
        print(f"Plotting {self.plot_kwargs['case_study'].project_name}...")
        max_cols = 5  # Number of columns in the grid
        # Hard coded for testing
        metric = self.plot_kwargs["metric"]
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        # Load the data for the case study
        df = aggregate_data(case_study, None)

        if df.empty:
            print(f"No data for {case_study.project_name}")
            return

        # If a value for the config_ids argument is None, replace it by -1
        df["config_id"] = df["config_id"].fillna(value=-1)

        # Filter data based on argument selection
        df = df[(df["metric"] == metric)]

        # TODO: Only keep significant results?
        if self.plot_kwargs.get("significant_only", False):

            def keep_significant(row: pd.Series) -> bool:
                if row["config_opportunity"] == "__baseline__":
                    return True
                return row["significance"].pvalue < 0.05

            df = df[df.apply(keep_significant, axis=1)]

        # Get all combinations of config_opportunity and variation that exist in the df
        elems = df[["config_id",
                    "binary-wl"]].drop_duplicates().apply(tuple,
                                                          axis=1).tolist()

        # Drop all combinations for which only the baseline exists
        elems = [(config_id, workload)
                 for config_id, workload in elems
                 if not df[(df["config_id"] == config_id) &
                           (df["binary-wl"] == workload) &
                           (df["config_opportunity"] != "__baseline__")].empty]

        # Use subfigures for better layout control
        nrows = (
            len(elems) + (max_cols - 1)
        ) // max_cols  # Round up to the nearest whole number

        fwidth = 8
        fheight = 8
        fig = plt.figure(figsize=(fwidth * max_cols, nrows * fheight))
        sfigs = fig.subfigures(
            nrows=nrows, ncols=max_cols, wspace=0.1, hspace=0.3
        )

        for i, (config_id, workload) in enumerate(elems):
            sf = sfigs[i // 5, i % 5]

            ax1 = sf.subplots(1, 1)
            fig_df = df[(df["config_id"] == config_id) &
                        (df["binary-wl"] == workload)]

            # Absolute mode
            base = np.mean(
                *fig_df[fig_df["config_opportunity"] == "__baseline__"]["value"]
            )

            # Add secondary x-axis for relative change
            ax1.set_xlabel("Absolute Value")

            fig_df = fig_df[fig_df["config_opportunity"] != "__baseline__"]

            _create_min_max_plot(
                fig_df,
                x="value",
                cat_col="config_opportunity",
                ax=ax1,
                baseline_val=base
            )
            secax = ax1.secondary_xaxis(
                'top',
                functions=(
                    lambda x, b=base: (x - b) / b, lambda x, b=base: x * b + b
                )
            )
            secax.set_xlabel("Relative Change")
            secax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0))
            ax1.set_title(f"Config {config_id}|{workload}")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return set()


class MinMaxAlternativesGenerator(
    PlotGenerator,
    generator_name="min-max-alternatives",
    options=[
        make_cli_option(
            "--case-studies",
            type=create_multi_case_study_choice(),
            required=True,
            help="Case studies to plot",
        ),
        make_cli_option(
            "--metric",
            # Type should be a comma-separated list of metrics
            type=click.Choice(["wall_clock_time", "max_resident_size"]),
            required=True,
            help="Metric to plot.",
        ),
        make_cli_option(
            "--significant-only",
            is_flag=True,
            default=False,
            help="Only plot significant results (p-value < 0.05).",
        )
    ]
):

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs["case_studies"]
        self.plot_kwargs.pop("case_studies", None)
        return [
            MinMaxAlternativesPlot(
                self.plot_config, **self.plot_kwargs, case_study=cs
            ) for cs in case_studies
        ]


def _create_min_max_plot(
    data: pd.DataFrame,
    x: str,
    cat_col: str,
    ax: Axes,
    baseline_val: float = 0.0
) -> None:
    categories = data[cat_col].unique()
    y_pos = np.arange(len(categories))

    data = data.explode(x)

    required_cols = [cat_col, x, "variation"]
    rem_cols = [col for col in data.columns if col not in required_cols]
    data = data.drop(columns=rem_cols)

    for i, category in enumerate(categories):
        cat_data = data[data[cat_col] == category]
        cat_data = cat_data.drop(columns=[cat_col])

        min_val = cat_data[x].min()
        max_val = cat_data[x].max()

        if min_val < baseline_val:
            bar = ax.barh(
                y_pos[i],
                min(baseline_val, max_val) - min_val,
                left=min_val,
                color='palegreen'
            )
        if max_val > baseline_val:
            bar = ax.barh(
                y_pos[i],
                max_val - max(baseline_val, min_val),
                left=max(baseline_val, min_val),
                color='lightcoral'
            )

        # Add vlines for all individual values
        ax.vlines(
            cat_data[x],
            y_pos[i] - (bar[0].get_height() / 2),
            y_pos[i],
            color='black',
            linewidth=1,
            alpha=0.6
        )

        # Add vlines for mean values per variation
        mean_vals = cat_data.groupby("variation").mean()
        ax.vlines(
            mean_vals[x],
            y_pos[i],
            y_pos[i] + (bar[0].get_height() / 2),
            color='black',
            linewidth=1,
            alpha=0.6
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.axvline(
        baseline_val, color='red', linewidth=0.8
    )  # Baseline line for the middle

    # Set x-axis limits
    g_min = data[x].min()
    g_max = data[x].max()
    range_span = max(abs(baseline_val - g_min), abs(baseline_val - g_max))
    ax.set_xlim(
        baseline_val - 1.05 * range_span, baseline_val + 1.05 * range_span
    )

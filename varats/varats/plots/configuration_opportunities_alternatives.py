import typing as tp
from functools import cmp_to_key

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
    create_config_opportunities_value_map,
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
from varats.ts_utils.click_param_types import (
    create_multi_case_study_choice,
    create_single_case_study_choice,
)
from varats.utils.git_util import FullCommitHash


def _prepare_data(plot_kwargs, df: pd.DataFrame) -> pd.DataFrame:
    """Filter the DataFrame to only include relevant data."""
    metric = plot_kwargs["metric"]

    # If a value for the config_ids argument is None, replace it by -1
    df["config_id"] = df["config_id"].fillna(value=-1)
    if plot_kwargs["config_opportunity"] is not None:
        config_opportunity = plot_kwargs["config_opportunity"]
        df = df[(df["config_opportunity"] == config_opportunity) |
                (df["config_opportunity"] == "__baseline__")]

    # Filter data based on argument selection
    df = df[(df["metric"] == metric)]

    # Filter data based on config_id
    if "config_id" in plot_kwargs:
        config_id = plot_kwargs["config_id"]
        if config_id is None:
            config_id = -1
        df = df[df["config_id"] == config_id]

    if workload := plot_kwargs.get("workload"):
        df = df[df["binary-wl"] == workload]

    if plot_kwargs.get("significant_only", False):

        def keep_significant(row: pd.Series) -> bool:
            if row["config_opportunity"] == "__baseline__":
                return True
            return row["significance"].pvalue < 0.05

        df = df[df.apply(keep_significant, axis=1)]

    str_val_map = create_config_opportunities_value_map(
        plot_kwargs["case_study"]
    )

    def map_str_values(row: pd.Series) -> pd.Series:
        """Map string values to numerical values."""
        if row["config_opportunity"] == "__baseline__":
            return row
        row["variation"] = str_val_map[row["config_opportunity"]][str(
            row["variation"]
        )]
        return row

    df = df.apply(map_str_values, axis=1)

    return df


class OpportunitiesStackedDistPlot(
    Plot, plot_name="opportunities_stacked_dist"
):

    @property
    def name(self) -> str:
        """Returns the name of the plot."""
        name = f"{self.NAME}_{self.plot_kwargs['metric']}"
        if self.plot_kwargs["config_opportunity"] is not None:
            name += f"_{self.plot_kwargs['config_opportunity'].replace('/', '+')}"
        if self.plot_kwargs["significant_only"]:
            name += "_significant"
        return name

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        print(
            f"Plotting {self.plot_kwargs['metric']} for {self.plot_kwargs['case_study'].project_name} with opportunity {self.plot_kwargs['config_opportunity']}..."
        )

        df = aggregate_data(case_study, None)
        df = _prepare_data(self.plot_kwargs, df)

        if df.empty:
            print(f"No data for {case_study.project_name}")
            return

        category_col = "config_opportunity"
        if self.plot_kwargs["config_opportunity"] is not None:
            category_col = "variation"

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

        max_cols = 5
        # Use subfigures for better layout control
        nrows = (
            len(elems) + (max_cols - 1)
        ) // max_cols  # Round up to the nearest whole number

        fwidth = 8
        fheight = 24
        fig = plt.figure(
            figsize=(fwidth * max_cols, nrows * fheight),
            constrained_layout=False
        )
        fig.suptitle(
            f"{case_study.project_name} - {self.plot_kwargs['metric']}"
        )

        splots = fig.subplots(nrows=nrows, ncols=max_cols, squeeze=False)

        fig.subplots_adjust(hspace=0.1)

        for i, (config_id, workload) in enumerate(elems):
            ax1 = splots[i // 5, i % 5]

            fig_df = df[(df["config_id"] == config_id) &
                        (df["binary-wl"] == workload)]

            # Absolute mode
            base = np.mean(
                *fig_df[fig_df["config_opportunity"] == "__baseline__"]["value"]
            )

            # Add the secondary x-axis for relative change
            ax1.set_xlabel("Absolute Value")

            # Keep Baseline row only for plots that show the config opportunity explicitly
            if self.plot_kwargs["config_opportunity"] is not None:
                fig_df.loc[:, "variation"] = fig_df["variation"].fillna(value=0)

            fig_df = fig_df.explode("value")
            # Create a stacked violin plot
            sns.violinplot(
                data=fig_df,
                x="value",
                y=category_col,
                orient="h",
                ax=ax1,
            )

            # y_ticks = [l.get_text for l in ax1.get_yticklabels()]
            # y_ticks = [l if l != "0.0" else "Base" for l in y_ticks]

            #ax1.set_yticklabels(y_ticks)

            secax = ax1.secondary_xaxis(
                'top',
                functions=(
                    lambda x, b=base: (x - b) / b, lambda x, b=base: x * b + b
                )
            )
            secax.set_xlabel("Relative Change")
            secax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0))
            ax1.set_title(f"Config {config_id}|{workload}")

    plt.tight_layout()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass


class OpportunitiesStackedDistGenerator(
    PlotGenerator,
    generator_name="opportunities_stacked_dist",
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
        ),
        make_cli_option(
            "--config-opportunity",
            type=str,
            required=False,
            help=
            "Show a detailed view for a specific config_opportunity. Will plot bars for each variation of the config_opportunity.",
        )
    ]
):
    """Generates the configuration opportunities distribution plot."""

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs["case_studies"]
        self.plot_kwargs.pop("case_studies", None)
        self.plot_kwargs.pop("metric", None)
        self.plot_kwargs.pop("config_opportunity", None)

        plots = []

        for cs in case_studies:
            # Get config opportunities for the case study
            opportunities = create_config_opportunities_value_map(cs)

            plots += [
                OpportunitiesStackedDistPlot(
                    self.plot_config,
                    **self.plot_kwargs,
                    case_study=cs,
                    config_opportunity=opportunity,
                    metric=m
                )
                for opportunity in opportunities
                for m in ["wall_clock_time", "max_resident_size"]
            ]
        return plots


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
                ] = base[:3] + (alpha,)  # Modify alpha but keep the RGB part

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

        # Load data for the first config to get the number of binaries
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

                # Set the titles for the first col/row
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

                # Create the strip plot for relative change below
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
        name = f"{self.NAME}_{self.plot_kwargs['metric']}"
        if self.plot_kwargs["config_opportunity"] is not None:
            name += f"_config_{self.plot_kwargs['config_opportunity'].replace('/', '+')}"
        if self.plot_kwargs["significant_only"]:
            name += "_significant"
        return name

    def plot(self, view_mode: bool) -> None:
        print(
            f"Plotting {self.plot_kwargs['metric']} for {self.plot_kwargs['case_study'].project_name} with opportunity {self.plot_kwargs['config_opportunity']}..."
        )
        if self.plot_kwargs["config_opportunity"] is not None:
            print(f"({self.plot_kwargs['config_opportunity']})")

        max_cols = 5  # Number of columns in the grid
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        # Load the data for the case study
        df = aggregate_data(case_study, None)
        df = _prepare_data(self.plot_kwargs, df)

        if df.empty:
            print(f"No data for {case_study.project_name}")
            return

        category_col = "config_opportunity"
        draw_means = True
        if self.plot_kwargs["config_opportunity"] is not None:
            category_col = "variation"
            draw_means = False

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
        fig.suptitle(
            f"{case_study.project_name} - {self.plot_kwargs['metric']}"
        )
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

            # Add the secondary x-axis for relative change
            ax1.set_xlabel("Absolute Value")

            # Keep Baseline row only for plots that show the config opportunity explicitly
            if "config_opportunity" not in self.plot_kwargs:
                fig_df = fig_df[fig_df["config_opportunity"] != "__baseline__"]
            else:
                fig_df.loc[:, "variation"] = fig_df["variation"].fillna(
                    value="Base"
                )

            _create_min_max_plot(
                fig_df,
                x="value",
                cat_col=category_col,
                ax=ax1,
                baseline_val=base,
                draw_mean=draw_means
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
        ),
        make_cli_option(
            "--config-opportunity",
            type=str,
            required=False,
            help=
            "Show a detailed view for a specific config_opportunity. Will plot bars for each variation of the config_opportunity.",
        )
    ]
):

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs["case_studies"]
        self.plot_kwargs.pop("case_studies", None)
        self.plot_kwargs.pop("metric", None)
        self.plot_kwargs.pop("config_opportunity", None)

        plots = []

        for cs in case_studies:
            # Get config opportunities for the case study
            opportunities = create_config_opportunities_value_map(cs)

            plots += [
                MinMaxAlternativesPlot(
                    self.plot_config,
                    **self.plot_kwargs,
                    case_study=cs,
                    config_opportunity=opportunity,
                    metric=m
                )
                for opportunity in opportunities
                for m in ["wall_clock_time", "max_resident_size"]
            ]
        return plots


class SingleMinMaxAlternativesPlot(
    Plot, plot_name="single_min_max_alternatives"
):

    @property
    def name(self) -> str:
        """Returns the name of the plot."""
        name = f"{self.NAME}_{self.plot_kwargs['config_id']}_{self.plot_kwargs['metric']}"
        if self.plot_kwargs["config_opportunity"] is not None:
            name += f"_{self.plot_kwargs['config_opportunity'].replace('/', '+')}"
        name += f"_{self.plot_kwargs['workload'].replace('/', '+')}"
        return name

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        # Optional data cache that can be passed to the plot
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        metric: str = self.plot_kwargs["metric"]
        config_id: tp.Optional[int] = self.plot_kwargs["config_id"]
        workload: str = self.plot_kwargs["workload"]

        if config_id == -1:
            config_id = None

        if "data_cache" in self.plot_kwargs:
            df = self.plot_kwargs["data_cache"]
        else:
            df = get_data_for_single_config(case_study, config_id)

        df = _prepare_data(self.plot_kwargs, df)

        category_col = "config_opportunity"
        draw_means = True
        if self.plot_kwargs["config_opportunity"] is not None:
            category_col = "variation"
            draw_means = False

        ax = plt.axes()

        # Absolute mode
        base = np.mean(*df[df["config_opportunity"] == "__baseline__"]["value"])

        # Add the secondary x-axis for relative change
        ax.set_xlabel("Absolute Value")

        # Keep Baseline row only for plots that show the config opportunity explicitly
        if "config_opportunity" not in self.plot_kwargs:
            df = df[df["config_opportunity"] != "__baseline__"]
        else:
            df.loc[:, "variation"] = df["variation"].fillna(value="Base")

        _create_min_max_plot(
            df,
            x="value",
            cat_col=category_col,
            ax=ax,
            baseline_val=base,
            draw_mean=draw_means
        )

        secax = ax.secondary_xaxis(
            'top',
            functions=(
                lambda x, b=base: (x - b) / b, lambda x, b=base: x * b + b
            )
        )
        secax.set_xlabel("Relative Change")
        secax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0))


class SingleStackedDistPlot(Plot, plot_name="single_stacked_dist"):

    @property
    def name(self) -> str:
        """Returns the name of the plot."""
        name = f"{self.NAME}_{self.plot_kwargs['config_id']}_{self.plot_kwargs['metric']}"
        if self.plot_kwargs["config_opportunity"] is not None:
            name += f"_{self.plot_kwargs['config_opportunity'].replace('/', '+')}"
        name += f"_{self.plot_kwargs['workload'].replace('/', '+')}"
        return name

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        pass

    def plot(self, view_mode: bool) -> None:
        # Optional data cache that can be passed to the plot
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        metric: str = self.plot_kwargs["metric"]
        config_id: tp.Optional[int] = self.plot_kwargs["config_id"]
        workload: str = self.plot_kwargs["workload"]

        if config_id == -1:
            config_id = None

        if "data_cache" in self.plot_kwargs:
            df = self.plot_kwargs["data_cache"]
        else:
            df = get_data_for_single_config(case_study, config_id)

        df = _prepare_data(self.plot_kwargs, df)

        category_col = "config_opportunity"
        if self.plot_kwargs["config_opportunity"] is not None:
            category_col = "variation"

        fig = plt.figure(figsize=(8, 2 * len(df[category_col].unique())))

        # Absolute mode
        base = np.mean(*df[df["config_opportunity"] == "__baseline__"]["value"])

        # Keep Baseline row only for plots that show the config opportunity explicitly
        if "config_opportunity" not in self.plot_kwargs:
            df = df[df["config_opportunity"] != "__baseline__"]
        else:
            df.loc[:, "variation"] = df["variation"].fillna(value="Base")

        df = df.explode("value")

        ax = sns.violinplot(
            data=df,
            x="value",
            y=category_col,
            orient="h",
        )

        # Add the secondary x-axis for relative change
        ax.set_xlabel("Absolute Value")

        secax = ax.secondary_xaxis(
            'top',
            functions=(
                lambda x, b=base: (x - b) / b, lambda x, b=base: x * b + b
            )
        )
        secax.set_xlabel("Relative Change")
        secax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0))


class SingleMinMaxAlternativesGenerator(
    PlotGenerator,
    generator_name="single_min_max_alternatives",
    options=[
        make_cli_option(
            "--case-study",
            type=create_single_case_study_choice(),
            required=True,
            help="Case study to plot",
        ),
        make_cli_option(
            "--metric",
            # Type should be a comma-separated list of metrics
            type=click.Choice(["wall_clock_time", "max_resident_size"]),
            required=True,
            help="Metric to plot.",
        ),
        make_cli_option(
            "--config-opportunity",
            type=str,
            required=False,
            help=
            "Show a detailed view for a specific config_opportunity. Will plot bars for each variation of the config_opportunity.",
        ),
        make_cli_option(
            "--config_id",
            type=int,
            required=True,
            help="Draw mean values for each variation.",
        ),
        make_cli_option(
            "--workload",
            type=str,
            required=True,
            help=
            "Workload to plot (e.g. 'binary/workload'). This is used to filter the data.",
        )
    ]
):
    """Generates the single configuration min-max alternatives plot."""

    def generate(self) -> tp.List[Plot]:
        return [
            SingleMinMaxAlternativesPlot(self.plot_config, **self.plot_kwargs)
        ]


class SingleStackedDistGenerator(
    PlotGenerator,
    generator_name="single_stacked_dist",
    options=[
        make_cli_option(
            "--case-study",
            type=create_single_case_study_choice(),
            required=True,
            help="Case study to plot",
        ),
        make_cli_option(
            "--metric",
            # Type should be a comma-separated list of metrics
            type=click.Choice(["wall_clock_time", "max_resident_size"]),
            required=True,
            help="Metric to plot.",
        ),
        make_cli_option(
            "--config-opportunity",
            type=str,
            required=False,
            help=
            "Show a detailed view for a specific config_opportunity. Will plot bars for each variation of the config_opportunity.",
        ),
        make_cli_option(
            "--config_id",
            type=int,
            required=True,
            help="Draw mean values for each variation.",
        ),
        make_cli_option(
            "--workload",
            type=str,
            required=True,
            help=
            "Workload to plot (e.g. 'binary/workload'). This is used to filter the data.",
        )
    ]
):
    """Generates the single configuration min-max alternatives plot."""

    def generate(self) -> tp.List[Plot]:
        return [SingleStackedDistPlot(self.plot_config, **self.plot_kwargs)]


def _create_min_max_plot(
    data: pd.DataFrame,
    x: str,
    cat_col: str,
    ax: Axes,
    baseline_val: float = 0.0,
    draw_mean: bool = True
) -> None:

    def cmp(item1, item2) -> int:
        if isinstance(item1, str):
            return -1
        if isinstance(item2, str):
            return 1

        return item1 - item2

    categories = sorted(data[cat_col].unique(), key=cmp_to_key(cmp))
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

        if min_val <= baseline_val:
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

        vline_end = y_pos[i]
        if not draw_mean:
            vline_end += (bar[0].get_height() / 2)

        # Add vlines for all individual values
        ax.vlines(
            cat_data[x],
            y_pos[i] - (bar[0].get_height() / 2),
            vline_end,
            color='black',
            linewidth=1,
            alpha=0.6
        )

        if draw_mean:
            # Add vlines for mean values per variation
            mean_vals = cat_data.groupby("variation").mean()
            ax.vlines(
                mean_vals[x],
                vline_end,
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

import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.figure import SubFigure
from matplotlib.ticker import PercentFormatter

from varats.data.databases.hidden_configurability_database import (
    aggregate_date,
    create_config_opportunities_value_map,
    get_data_for_single_config,
    get_configuration_points,
    extract_config_point,
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


class ConfAlternativesDetailPlot(
    Plot, plot_name="configuration_opportunities_details"
):

    @property
    def name(self) -> str:
        return f"{self.NAME}_{self.plot_kwargs['metric']}"

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

        df = aggregate_date(case_study, configs)

        # Filter for relevant metric & Filter out baseline
        df = df[(df["metric"] == f"{metric}_relative") &
                (df["config_opportunity"] != "__baseline__")]

        if df.empty:
            print(f"No data for {case_study.project_name} ({configs=})")
            return

        # Transform variation values from strings to their actual values
        config_opportunity_map = create_config_opportunities_value_map(
            case_study
        )

        df["variation"] = df.apply(
            lambda row: config_opportunity_map[row["config_opportunity"]][row[
                "variation"]],
            axis=1
        )

        binaries = df["binary-wl"].unique()
        config_vars = df["config_opportunity"].unique()
        fig = plt.figure(figsize=(8 * len(config_vars), 8 * len(binaries)))
        sfigs = fig.subplots(
            nrows=len(binaries), ncols=len(config_vars), squeeze=False
        )

        for bin_idx, binary in enumerate(binaries):
            for conf_idx, config_var in enumerate(config_vars):
                # Plot the relative values
                data_df = df[(df["binary-wl"] == binary) &
                             (df["config_opportunity"] == config_var)]

                subfig: Axes = sfigs[bin_idx, conf_idx]

                sns.jointplot(
                    data_df,
                    y="variation",
                    x="value",
                    hue="config_id",
                    ax=subfig
                )

                # Arrange things
                subfig.legend().remove()
                subfig.set_xticklabels(
                    subfig.get_xticklabels(), rotation=90, ha='right'
                )
                subfig.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
                subfig.set_title(f"{binary} ({config_var})")
                subfig.set_ylabel(f"{metric} (Relative)")
                subfig.set_xlabel("")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        return set()


class ConfigurationAlternativesDetailGenerator(
    PlotGenerator,
    generator_name="co-alt-detail",
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
            required=False,
            default="wall_clock_time,max_resident_size",
            help="Metrics to plot (e.g. wall_clock_time,max_resident_size)",
        )
    ]
):

    def generate(self) -> tp.List[Plot]:
        return [
            ConfAlternativesDetailPlot(
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
                metric_rel_df = binary_df[binary_df["metric"] ==
                                          f"{metric}_relative"]

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
                    y="value",
                    x="config_opportunity",
                    hue="config_var",
                    data=metric_rel_df,
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

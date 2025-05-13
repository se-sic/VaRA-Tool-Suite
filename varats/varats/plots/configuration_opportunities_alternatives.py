import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import to_rgba
from matplotlib.ticker import PercentFormatter

from varats.data.reports.hidden_configurability_report import MPRTimeWLAggregate
from varats.experiments.vara.hidden_configurability_experiments import (
    TimePatchedWorkloads,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.gnu_time_report import (
    WLTimeReportAggregate,
    TimeReportAggregate,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import FullCommitHash


def extract_config_point(full_name: str) -> tp.Tuple[str, str]:
    # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
    # We are interested in the unique configuration points
    name_parts = full_name.split("_")
    config_point = name_parts[-1].split("=")
    return config_point[0], config_point[1].split('.')[0]


def get_configuration_points(report_file: MPRTimeWLAggregate) -> tp.List[str]:
    result = set()

    for patch_name in report_file.get_patch_names():
        # patch names follow the pattern "<patch_name>_<base_file_name>_<config_point>=<value>"
        # We are interested in the unique configuration points
        result.add(extract_config_point(patch_name)[0])

    return list(result)


def _aggregate_data(cs: CaseStudy, config_id: int) -> pd.DataFrame:
    result = pd.DataFrame()

    result_files = get_processed_revisions_files(
        cs.project_name,
        TimePatchedWorkloads,
        TimePatchedWorkloads.report_spec().main_report,
        get_case_study_file_name_filter(cs),
        config_id=config_id
    )

    if len(result_files) == 0:
        print(f"No results found for {cs.project_name} ({config_id=})")
        return pd.DataFrame()

    data_rows = []

    base_times = {}
    base_rss = {}

    for result_file in result_files:
        report: MPRTimeWLAggregate = MPRTimeWLAggregate(result_file.full_path())

        binary = report.filename.binary_name

        base_report: WLTimeReportAggregate = report.get_baseline_report()

        for wl in base_report.workload_names():
            data_rows.extend([{
                "binary-wl": f"{binary}/{wl}",
                "config_opportunity": "__baseline__",
                "variation": None,
                "metric": "wall_clock_time",
                "value": base_report.measurements_wall_clock_time(wl),
            }, {
                "binary-wl": f"{binary}/{wl}",
                "config_opportunity": "__baseline__",
                "variation": None,
                "metric": "max_resident_size",
                "value": base_report.max_resident_sizes(wl),
            }])

            base_times[wl] = np.mean(
                base_report.measurements_wall_clock_time(wl)
            )
            base_rss[wl] = np.mean(base_report.max_resident_sizes(wl))

        for patch_report in report.get_patched_reports():
            cp = extract_config_point(patch_report.filename.filename)
            for wl in patch_report.workload_names():
                data_rows.extend([{
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": cp[0],
                    "variation": cp[1],
                    "metric": "wall_clock_time",
                    "value": patch_report.measurements_wall_clock_time(wl),
                }, {
                    "binary-wl": f"{binary}/{wl}",
                    "config_opportunity": cp[0],
                    "variation": cp[1],
                    "metric": "max_resident_size",
                    "value": patch_report.max_resident_sizes(wl),
                }, {
                    "binary-wl":
                        f"{binary}/{wl}",
                    "config_opportunity":
                        cp[0],
                    "variation":
                        cp[1],
                    "metric":
                        "wall_clock_time_relative",
                    "value": (
                        np.mean(patch_report.measurements_wall_clock_time(wl)) /
                        base_times[wl]
                    ) - 1,
                }, {
                    "binary-wl":
                        f"{binary}/{wl}",
                    "config_opportunity":
                        cp[0],
                    "variation":
                        cp[1],
                    "metric":
                        "max_resident_size_relative",
                    "value": (
                        np.mean(patch_report.max_resident_sizes(wl)) /
                        base_rss[wl]
                    ) - 1,
                }])

    result = pd.DataFrame.from_records(data_rows)

    return result


class ConfigurationAlternativesAggPlot(
    Plot, plot_name="configuration_opportunities_alternatives_agg"
):
    """Plot that provides a concise overview of configuration alternatives for
    all configurations, workloads and binaries."""

    @property
    def name(self) -> str:
        return f"{self.NAME}_{self.plot_kwargs['config_id']}"

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
        case_study = self.plot_kwargs["case_study"]
        config_id = self.plot_kwargs["config_id"]

        df = _aggregate_data(case_study, config_id)

        if df.empty:
            print(f"No data for {case_study.project_name} ({config_id=})")
            return

        binaries = df["binary-wl"].unique()

        time_palette = self.__create_palettes(
            df[df["metric"] == "wall_clock_time"]
        )
        rss_palette = self.__create_palettes(
            df[df["metric"] == "max_resident_size"]
        )

        df["value"] = df["value"].apply(np.mean)
        df["config_var"] = list(zip(df['config_opportunity'], df['variation']))

        fig = plt.figure(figsize=(8 * len(binaries), 8))
        sfigs = fig.subfigures(1, len(binaries), squeeze=False)

        for i, binary in enumerate(binaries):
            baseline_df = df[(df["binary-wl"] == binary) &
                             (df["config_opportunity"] == "__baseline__")]

            binary_df = df[(df["binary-wl"] == binary) &
                           (df["config_opportunity"] != "__baseline__")]

            time_df = binary_df[binary_df["metric"] == "wall_clock_time"]
            time_rel_df = binary_df[binary_df["metric"] ==
                                    "wall_clock_time_relative"]
            rss_df = binary_df[binary_df["metric"] == "max_resident_size"]
            rss_rel_df = binary_df[binary_df["metric"] ==
                                   "max_resident_size_relative"]

            axes = sfigs[0, i].subplots(2, 2)

            # Create one strip plot in column 0 for wall clock time
            sns.stripplot(
                ax=axes[0, 0],
                y="value",
                x="config_opportunity",
                hue="config_var",
                data=time_df,
                palette=time_palette,
            )

            # Create another strip plot in column 0 for wall clock time relative
            sns.stripplot(
                ax=axes[1, 0],
                y="value",
                x="config_opportunity",
                hue="config_var",
                data=time_rel_df,
                palette=time_palette,
            )

            # Create another strip plot in column 1 for max resident size
            sns.stripplot(
                ax=axes[0, 1],
                y="value",
                x="config_opportunity",
                hue="config_var",
                data=rss_df,
                palette=rss_palette,
            )

            # Create another strip plot in column 1 for max resident size relative
            sns.stripplot(
                ax=axes[1, 1],
                y="value",
                x="config_opportunity",
                hue="config_var",
                data=rss_rel_df,
                palette=rss_palette,
            )

            # Draw the baseline line for absolute plots
            axes[0, 0].axhline(
                y=np.mean(
                    baseline_df[baseline_df["metric"] == "wall_clock_time"]
                    ["value"]
                ),
                color='red',
                linestyle='--',
                linewidth=1,
                label="Baseline"
            )

            axes[0, 1].axhline(
                y=np.mean(
                    baseline_df[baseline_df["metric"] == "max_resident_size"]
                    ["value"]
                ),
                color='red',
                linestyle='--',
                linewidth=1,
                label="Baseline"
            )

            for idx in range(2):
                # Set yticks to the right
                axes[idx, 1].yaxis.tick_right()
                axes[1, idx].set_ylim(-0.5, 0.5)
                axes[1,
                     idx].yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
                axes[1, idx].axhline(
                    y=0, color='black', linestyle='--', linewidth=1
                )

            for ax in axes.flatten():
                ax.legend().remove()
                ax.set_xticklabels([])
                ax.set_ylabel("")
                ax.set_xlabel("")


class ConfigurationAlternativesAggGenerator(
    PlotGenerator, generator_name="co-alt-agg", options=[]
):
    """Generates the configuration opportunities runtime plot."""

    def generate(self) -> tp.List[Plot]:
        generators = []

        for cs in get_loaded_paper_config().get_all_case_studies():
            if cs.project_name not in [
                #"DunePerfRegression", "brotli", "libvpx", "libzmq"
                "brotli"
            ]:
                continue
            if len(cs.get_config_ids_for_revision(cs.revisions[0])) == 0:
                generators.append(
                    ConfigurationAlternativesAggPlot(
                        self.plot_config,
                        case_study=cs,
                        config_id=None,
                        **self.plot_kwargs
                    )
                )
            else:
                generators.extend([
                    ConfigurationAlternativesAggPlot(
                        self.plot_config,
                        case_study=cs,
                        config_id=c_id,
                        **self.plot_kwargs
                    )
                    for c_id in cs.get_config_ids_for_revision(cs.revisions[0])
                ])

        return generators


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

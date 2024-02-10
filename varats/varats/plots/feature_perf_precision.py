"""Module for the FeaturePerfPrecision plots."""
import typing as tp
from itertools import chain

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.text import Text

from varats.data.databases.feature_perf_precision_database import (
    Profiler,
    VXray,
    PIMTracer,
    EbpfTraceTEF,
    load_precision_data,
    load_overhead_data,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class PerfPrecisionPlot(Plot, plot_name='fperf_precision'):
    """Precision plot that plots the precision and recall values of different
    profilers."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        df = pd.DataFrame()
        df = load_precision_data(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)

        grid = multivariate_grid(
            df,
            'precision',
            'recall',
            'Profiler',
            global_kde=False,
            alpha=0.7,
            legend=False,
            s=100
        )
        grid.ax_marg_x.set_xlim(0.0, 1.02)
        grid.ax_marg_y.set_ylim(0.0, 1.02)
        grid.ax_joint.legend([name for name, _ in df.groupby("Profiler")])

        grid.ax_joint.set_xlabel("Precision")
        grid.ax_joint.set_ylabel("Recall")
        grid.ax_joint.xaxis.label.set_size(20)
        grid.ax_joint.yaxis.label.set_size(20)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfPrecisionPlotGenerator(
    PlotGenerator, generator_name="fperf-precision", options=[]
):
    """Generates precision plot."""

    def generate(self) -> tp.List[Plot]:

        return [PerfPrecisionPlot(self.plot_config, **self.plot_kwargs)]


class PerfPrecisionDistPlot(Plot, plot_name='fperf_precision_dist'):
    """Precision plot that plots the precision and recall distributions of
    different profilers."""

    def plot(self, view_mode: bool) -> None:
        case_studies = self.plot_kwargs["case_studies"]
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        df = pd.DataFrame()
        df = load_precision_data(case_studies, profilers)
        df.sort_values(["CaseStudy"], inplace=True)
        df = df.melt(
            id_vars=['CaseStudy', 'Patch', 'Profiler'],
            value_vars=['precision', 'recall'],
            var_name='metric',
            value_name="value"
        )

        colors = sns.color_palette("Paired", len(profilers) * 2)
        _, axes = plt.subplots(ncols=len(profilers), nrows=1, sharey=True)

        for idx, profiler in enumerate(profilers):
            ax = axes[idx]
            color_slice = colors[idx * 2:idx * 2 + 2]
            data_slice = df[df['Profiler'] == profiler.name]

            sns.violinplot(
                data=data_slice,
                x='Profiler',
                y='value',
                hue='metric',
                inner=None,
                cut=0,
                split=True,
                palette=color_slice,
                linewidth=1,
                ax=ax
            )

            sns.stripplot(
                data=data_slice,
                x="Profiler",
                y="value",
                hue="metric",
                jitter=0.15,
                dodge=True,
                linewidth=0.5,
                marker='x',
                palette=[
                    mcolors.XKCD_COLORS['xkcd:dark grey'],
                    mcolors.CSS4_COLORS['dimgrey']
                ],
                size=7,
                ax=ax
            )

            ax.get_legend().remove()

            ax.set_ylabel(None)
            ax.set_xlabel(None)
            ax.tick_params(axis='x', labelsize=10, pad=8, length=6, width=1)

            if idx == 0:
                ax.set_ylim(-0.1, 1.1)
                ax.tick_params(axis='y', labelsize=10)
                ax.tick_params(axis='y', width=1, length=3)
            else:
                ax.tick_params(left=False)

        plt.subplots_adjust(wspace=.0)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfProfDistPlotGenerator(
    PlotGenerator,
    generator_name="fperf-precision-dist",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates performance distribution plot for a given list of case
    studies."""

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs.pop("case_study")
        return [
            PerfPrecisionDistPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class PerfProfDistPlotGeneratorForEachCS(
    PlotGenerator,
    generator_name="fperf-precision-dist-cs",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates performance distribution plot for each of the given case
    studies."""

    def generate(self) -> tp.List[Plot]:
        case_studies = self.plot_kwargs.pop("case_study")
        return [
            PerfPrecisionDistPlot(
                self.plot_config,
                case_study=case_study,
                case_studies=[case_study],
                **self.plot_kwargs
            ) for case_study in case_studies
        ]


class PerfOverheadPlot(Plot, plot_name='fperf_overhead'):
    """Performance overhead plot that shows the pareto front of the different
    performance metrics."""

    def plot(self, view_mode: bool) -> None:
        # -- Configure plot --
        plot_metric = [
            ("Time", "overhead_time_rel"),
            ("Memory", "overhead_memory_rel"),
        ]
        extra_metrics = False
        if extra_metrics:
            plot_metric.extend([
                ("Major Page Faults", "overhead_major_page_faults_rel"),
                ("Minor Page Faults", "overhead_minor_page_faults_rel"),
                ("Filesystem Inputs", "overhead_fs_inputs_rel"),
                ("Filesystem Outputs", "overhead_fs_outputs_rel"),
            ])

        target_row = "f1_score"

        # Load data
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        full_precision_df = load_precision_data(case_studies, profilers)
        full_precision_df.sort_values(["CaseStudy"], inplace=True)

        precision_df = full_precision_df[[
            "CaseStudy", "precision", "recall", "Profiler", "f1_score"
        ]]
        precision_df = precision_df.groupby(['CaseStudy', "Profiler"],
                                            as_index=False).agg({
                                                'precision': 'mean',
                                                'recall': 'mean',
                                                'f1_score': 'mean'
                                            })

        overhead_df = load_overhead_data(case_studies, profilers)
        overhead_df['overhead_time_rel'] = overhead_df['time'] / (
            overhead_df['time'] - overhead_df['overhead_time']
        ) * 100

        overhead_df['overhead_memory_rel'] = overhead_df['memory'] / (
            overhead_df['memory'] - overhead_df['overhead_memory']
        ) * 100
        overhead_df['overhead_memory_rel'].replace([np.inf, -np.inf],
                                                   np.nan,
                                                   inplace=True)

        # Page faults
        overhead_df['overhead_major_page_faults_rel'
                   ] = overhead_df['major_page_faults'] / (
                       overhead_df['major_page_faults'] -
                       overhead_df['overhead_major_page_faults']
                   ) * 100
        overhead_df['overhead_major_page_faults_rel'].replace([np.inf, -np.inf],
                                                              np.nan,
                                                              inplace=True)

        overhead_df['overhead_minor_page_faults_rel'
                   ] = overhead_df['minor_page_faults'] / (
                       overhead_df['minor_page_faults'] -
                       overhead_df['overhead_minor_page_faults']
                   ) * 100
        overhead_df['overhead_minor_page_faults_rel'].replace([np.inf, -np.inf],
                                                              np.nan,
                                                              inplace=True)

        # Filesystem
        overhead_df['overhead_fs_inputs_rel'] = overhead_df['fs_inputs'] / (
            overhead_df['fs_inputs'] - overhead_df['overhead_fs_inputs']
        ) * 100
        overhead_df['overhead_fs_inputs_rel'].replace([np.inf, -np.inf],
                                                      np.nan,
                                                      inplace=True)

        overhead_df['overhead_fs_outputs_rel'] = overhead_df['fs_outputs'] / (
            overhead_df['fs_outputs'] - overhead_df['overhead_fs_outputs']
        ) * 100
        overhead_df['overhead_fs_outputs_rel'].replace([np.inf, -np.inf],
                                                       np.nan,
                                                       inplace=True)

        merged_df = pd.merge(
            precision_df, overhead_df, on=["CaseStudy", "Profiler"]
        )

        rows = 1
        _, axes = plt.subplots(
            ncols=int(len(plot_metric) / rows), nrows=rows, figsize=(30, 10)
        )

        if len(plot_metric) == 1:
            self.do_single_plot(
                plot_metric[0][1], target_row, merged_df, plot_metric[0][0],
                axes
            )
        else:
            if rows == 1:
                axes_list = list(axes)
            else:
                axes_list = list(chain.from_iterable(axes))

            for idx, ax in enumerate(axes_list):
                self.do_single_plot(
                    plot_metric[idx][1], target_row, merged_df,
                    plot_metric[idx][0], ax
                )

    def do_single_plot(
        self, x_values_name: str, target_row: str, merged_df: pd.DataFrame,
        plot_extra_name: str, ax: Axes
    ) -> None:
        """Plot a single overhead metric."""
        sns.scatterplot(
            merged_df,
            x=x_values_name,
            y=target_row,
            hue="Profiler",
            style='CaseStudy',
            alpha=0.5,
            s=300,
            ax=ax
        )

        text_obj: Text
        for text_obj in ax.legend().get_texts():

            text_obj.set_fontsize("xx-large")
            if text_obj.get_text() == "Profiler":
                text_obj.set_text("Profilers")
                text_obj.set_fontweight("bold")

            if text_obj.get_text() == "CaseStudy":
                text_obj.set_text("Subject Systems")
                text_obj.set_fontweight("bold")

        ax.set_xlabel(f"Relative {plot_extra_name}")
        if target_row == "f1_score":
            ax.set_ylabel("F1-Score")

        ax.set_ylim(0.0, 1.02)
        # Sets the limit at least to 150 or otherwise to the largest non
        # inf/nan value
        x_limit = max(
            np.max(
                np.nan_to_num(
                    merged_df[x_values_name],
                    copy=True,
                    nan=0.0,
                    posinf=0.0,
                    neginf=0.0
                )
            ) + 20, 120
        )
        ax.set_xlim(x_limit, 100)
        ax.tick_params(labelsize=20, pad=10)
        ax.xaxis.label.set_fontsize(25)
        ax.yaxis.label.set_fontsize(25)
        ax.yaxis.labelpad = 10
        ax.xaxis.labelpad = 20

        prof_df = merged_df[[
            'Profiler', 'precision', x_values_name, 'f1_score'
        ]].groupby('Profiler').agg(['mean', 'std'])
        prof_df.fillna(0, inplace=True)

        pareto_front = self.plot_pareto_frontier(
            prof_df[x_values_name]['mean'],
            prof_df[target_row]['mean'],
            max_x=False
        )

        pf_x = [pair[0] for pair in pareto_front]
        pf_y = [pair[1] for pair in pareto_front]

        x_loc = prof_df[x_values_name]['mean']
        y_loc = prof_df[target_row]['mean']
        x_error = prof_df[x_values_name]['std']
        y_error = prof_df[target_row]['std']

        ax.errorbar(
            x_loc,
            y_loc,
            xerr=x_error,
            yerr=y_error,
            fmt='none',
            color='grey',
            zorder=0,
            capsize=2,
            capthick=0.6,
            elinewidth=0.6
        )

        sns.scatterplot(
            prof_df,
            x=(x_values_name, 'mean'),
            y=(target_row, 'mean'),
            hue="Profiler",
            ax=ax,
            legend=False,
            s=300,
            zorder=2
        )

        sns.lineplot(
            x=pf_x,
            y=pf_y,
            ax=ax,
            color='firebrick',
            legend=False,
            linewidth=3.5,
            zorder=1
        )

    def plot_pareto_frontier(
        self,
        x_values: tp.List[float],
        y_values: tp.List[float],
        max_x: bool = True,
        max_y: bool = True
    ) -> tp.List[tp.List[float]]:
        """Pareto frontier selection process."""
        sorted_list = sorted([
            [x_values[i], y_values[i]] for i in range(len(x_values))
        ],
                             reverse=max_x)
        pareto_front = [sorted_list[0]]
        for pair in sorted_list[1:]:
            if max_y:
                if pair[1] >= pareto_front[-1][1]:
                    if pair[0] == pareto_front[-1][0]:
                        # If both points, have the same x-values, we should
                        # only keep the larger one
                        pareto_front[-1][1] = pair[1]
                    else:
                        pareto_front.append(pair)
            else:
                if pair[1] <= pareto_front[-1][1]:
                    if pair[0] == pareto_front[-1][0]:
                        # If both points, have the same x-values, we should
                        # only keep the smaller one
                        pareto_front[-1][1] = pair[1]
                    else:
                        pareto_front.append(pair)

        return pareto_front

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PerfOverheadPlotGenerator(
    PlotGenerator, generator_name="fperf-overhead", options=[]
):
    """Generates overhead plot."""

    def generate(self) -> tp.List[Plot]:
        return [PerfOverheadPlot(self.plot_config, **self.plot_kwargs)]

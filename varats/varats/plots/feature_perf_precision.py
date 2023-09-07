"""Module for the FeaturePerfPrecision plots."""
import random
import typing as tp
from itertools import chain

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
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
from varats.plot.plots import PlotConfig, PlotGenerator
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


def get_fake_prec_rows() -> tp.List[tp.Any]:
    fake_rows = []
    fake_prof = [("prof1", 10), ("prof2", 42)]
    for prof, seed in fake_prof:
        random.seed(seed)
        for _ in range(0, 3):
            x = random.random()
            y = random.random()
            new_fake_row = {
                'CaseStudy': "fake",
                'Patch': "fpatch",
                'Configs': 42,
                'RegressedConfigs': 21,
                'precision': x,
                'recall': y,
                'Profiler': prof
            }
            fake_rows.append(new_fake_row)

    return fake_rows


class PerfPrecisionPlot(Plot, plot_name='fperf_precision'):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        df = pd.DataFrame()
        df = load_precision_data(case_studies, profilers)
        # df = pd.concat([df, pd.DataFrame(get_fake_prec_rows())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

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

    def generate(self) -> tp.List[Plot]:

        return [PerfPrecisionPlot(self.plot_config, **self.plot_kwargs)]


class PerfPrecisionDistPlot(Plot, plot_name='fperf_precision_dist'):

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        profilers: tp.List[Profiler] = [VXray(), PIMTracer(), EbpfTraceTEF()]

        # Data aggregation
        df = pd.DataFrame()
        df = load_precision_data(case_studies, profilers)
        # df = pd.concat([df, pd.DataFrame(get_fake_prec_rows())])
        df.sort_values(["CaseStudy"], inplace=True)
        print(f"{df=}")

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


class PerfProfDistPlotGenerator(
    PlotGenerator, generator_name="fperf-precision-dist", options=[]
):

    def generate(self) -> tp.List[Plot]:

        return [PerfPrecisionDistPlot(self.plot_config, **self.plot_kwargs)]


class PerfOverheadPlot(Plot, plot_name='fperf_overhead'):

    def plot(self, view_mode: bool) -> None:
        # -- Configure plot --
        plot_metric = [("Time", "overhead_time_rel"),
                       ("Memory", "overhead_memory_rel"),
                       ("Major Page Faults", "overhead_major_page_faults_rel"),
                       ("Minor Page Faults", "overhead_minor_page_faults_rel"),
                       ("Filesystem Inputs", "overhead_fs_inputs_rel"),
                       ("Filesystem Outputs", "overhead_fs_outputs_rel")]
        target_row = "f1_score"
        # target_row = "precision"

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
        print(f"precision_df=\n{precision_df}")

        overhead_df = load_overhead_data(case_studies, profilers)
        print(f"{overhead_df=}")
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
        # TODO: fix
        overhead_df["overhead_major_page_faults_rel"].fillna(100, inplace=True)

        overhead_df['overhead_minor_page_faults_rel'
                   ] = overhead_df['minor_page_faults'] / (
                       overhead_df['minor_page_faults'] -
                       overhead_df['overhead_minor_page_faults']
                   ) * 100
        overhead_df['overhead_minor_page_faults_rel'].replace([np.inf, -np.inf],
                                                              np.nan,
                                                              inplace=True)
        # TODO: fix
        overhead_df["overhead_minor_page_faults_rel"].fillna(100, inplace=True)

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

        print(f"other_df=\n{overhead_df}")

        merged_df = pd.merge(
            precision_df, overhead_df, on=["CaseStudy", "Profiler"]
        )
        print(f"merged_df=\n{merged_df}")

        # print(f"{self.plot_config.width()}")

        rows = 3
        _, axes = plt.subplots(
            ncols=int(len(plot_metric) / rows), nrows=rows, figsize=(30, 10)
        )

        if len(plot_metric) == 1:
            self.do_single_plot(
                plot_metric[0][1], target_row, merged_df, plot_metric[0][0],
                axes
            )
        else:
            for idx, ax in enumerate(list(chain.from_iterable(axes))):
                self.do_single_plot(
                    plot_metric[idx][1], target_row, merged_df,
                    plot_metric[idx][0], ax
                )

    def do_single_plot(
        self, x_values, target_row, merged_df, plot_extra_name, ax
    ) -> None:
        # ax =
        sns.scatterplot(
            merged_df,
            x=x_values,
            y=target_row,
            hue="Profiler",
            style='CaseStudy',
            alpha=0.5,
            s=100,
            ax=ax
        )

        for text_obj in ax.legend().get_texts():
            text_obj: Text

            text_obj.set_fontsize("small")
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
                    merged_df[x_values],
                    copy=True,
                    nan=0.0,
                    posinf=0.0,
                    neginf=0.0
                )
            ) + 20, 120
        )
        ax.set_xlim(x_limit, 100)
        ax.xaxis.label.set_size(20)
        ax.yaxis.label.set_size(20)
        ax.tick_params(labelsize=15)

        prof_df = merged_df[['Profiler', 'precision', x_values, 'f1_score'
                            ]].groupby('Profiler').agg(['mean', 'std'])
        prof_df.fillna(0, inplace=True)

        print(f"{prof_df=}")
        pareto_front = self.plot_pareto_frontier(
            prof_df[x_values]['mean'], prof_df[target_row]['mean'], maxX=False
        )

        pf_x = [pair[0] for pair in pareto_front]
        pf_y = [pair[1] for pair in pareto_front]

        x_loc = prof_df[x_values]['mean']
        y_loc = prof_df[target_row]['mean']
        x_error = prof_df[x_values]['std']
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
            x=(x_values, 'mean'),
            y=(target_row, 'mean'),
            hue="Profiler",
            ax=ax,
            legend=False,
            s=100,
            zorder=2
        )

        sns.lineplot(
            x=pf_x,
            y=pf_y,
            ax=ax,
            color='firebrick',
            legend=False,
            linewidth=2.5,
            zorder=1
        )

    def plot_pareto_frontier(self, Xs, Ys, maxX=True, maxY=True):
        """Pareto frontier selection process."""
        sorted_list = sorted([[Xs[i], Ys[i]] for i in range(len(Xs))],
                             reverse=maxX)
        print(f"{sorted_list=}")
        pareto_front = [sorted_list[0]]
        for pair in sorted_list[1:]:
            if maxY:
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

    def generate(self) -> tp.List[Plot]:
        return [PerfOverheadPlot(self.plot_config, **self.plot_kwargs)]

"""Module for BlameInteractionGraph plots."""

import abc
import itertools
import typing as tp
from functools import reduce
from math import ceil, floor

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import Locator, FixedLocator, StrMethodFormatter

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    create_file_based_interaction_graph,
    AIGNodeAttrs,
    create_callgraph_based_interaction_graph,
)
from varats.data.reports.phasar_iter_ide import PhasarIterIDEStatsReport
from varats.experiments.phasar.iter_ide import (
    IDELinearConstantAnalysisExperiment,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.jupyterhelper.file import load_phasar_iter_ide_stats_report
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import (
    get_case_study_file_name_filter,
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.project.project_util import (
    get_local_project_git_path,
    get_project_cls_by_name,
)
from varats.report.gnu_time_report import TimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class PhasarIterIDEPlotBase(Plot, plot_name="phasar-iter-ide-plot"):
    YNAME = "Time"

    TAINT = "Taint"
    TYPESTATE = "Typestate"
    LCA = "LCA"

    JF1 = 0
    JF2 = 1
    JF3 = 2
    OLD = 3

    def __init_subclass__(
        cls,
        *,
        plot_name: tp.Optional[str],
        yname: tp.Optional[str] = None,
        **kwargs: tp.Any
    ) -> None:
        if yname:
            cls.YNAME = yname
        return super().__init_subclass__(plot_name=plot_name, **kwargs)

    def _get_aggregates(self, report: PhasarIterIDEStatsReport,
                        ana: str) -> tp.List[TimeReportAggregate]:
        if ana == self.TAINT:
            return [
                report.new_taint_jf1, report.new_taint, report.new_taint_jf3,
                report.old_taint
            ]
        elif ana == self.TYPESTATE:
            return [
                report.new_typestate_jf1, report.new_typestate,
                report.new_typestate_jf3, report.old_typestate
            ]
        elif ana == self.LCA:
            return [
                report.new_lca_jf1, report.new_lca, report.new_lca_jf3,
                report.old_lca
            ]
        else:
            raise "ERROR: Invalid analysis: " + ana

    @abc.abstractmethod
    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        pass

    def _get_jf_name(self, jf: int) -> str:
        if jf == self.JF1:
            return "JF1"
        elif jf == self.JF2:
            return "JF2"
        elif jf == self.JF3:
            return "JF2S"
        elif jf == self.OLD:
            return "Old"
        else:
            raise "ERROR: Table Rep out-of-range: " + str(jf)

    def make_dataframe(self) -> pd.DataFrame:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for case_study in case_studies:
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

            for report_file in report_files:
                report = load_phasar_iter_ide_stats_report(report_file)
                nodes.extend(
                    self._get_data_entries(report, case_study.project_name)
                )

        return pd.DataFrame(nodes).sort_values(by=["Analysis", "JF"])

    def broken_boxplot(
        self,
        data: pd.DataFrame,
        ratio: tp.List[int],
        lower_top_bot_step: tp.List[int],
        upper_top_bot_step: tp.List[int],
        break_space=0.1
    ):
        # See: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/broken_axis.html
        #
        # If we were to simply plot pts, we'd lose most of the interesting
        # details due to the outliers. So let's 'break' or 'cut-out' the y-axis
        # into two portions - use the top (ax1) for the outliers, and the bottom
        # (ax2) for the details of the majority of our data

        # fig, (ax1, ax2) = matplotlib.pyplot.subplots(2, 1, sharex = True)

        fig = plt.figure()

        gs = GridSpec(2, 2, height_ratios=ratio[:2])

        ax1 = fig.add_subplot(gs.new_subplotspec((0, 0), colspan=2))
        ax2 = fig.add_subplot(gs.new_subplotspec((1, 0), colspan=2))

        fig.subplots_adjust(hspace=break_space)  # adjust space between axes
        fig.text(0.02, 0.5, self.YNAME, va="center", rotation="vertical")

        ax1.set_yticks(
            np.arange(
                upper_top_bot_step[1] -
                upper_top_bot_step[1] % upper_top_bot_step[2],
                upper_top_bot_step[0], upper_top_bot_step[2]
            )
        )
        ax2.set_yticks(
            np.arange(
                lower_top_bot_step[1] -
                lower_top_bot_step[1] % lower_top_bot_step[2],
                lower_top_bot_step[0] + 1, lower_top_bot_step[2]
            )
        )

        sns.boxplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            ax=ax1,
        )
        sns.boxplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            ax=ax2,
        )

        # zoom-in / limit the view to different portions of the data
        ax1.set_ylim(
            top=upper_top_bot_step[0], bottom=upper_top_bot_step[1]
        )  # outliers only
        ax2.set_ylim(
            top=lower_top_bot_step[0], bottom=lower_top_bot_step[1]
        )  # most of the data

        # hide the spines between ax and ax2
        ax1.spines.bottom.set_visible(False)
        ax2.spines.top.set_visible(False)
        ax1.xaxis.tick_top()
        ax1.tick_params(labeltop=False)  # don't put tick labels at the top
        ax2.xaxis.tick_bottom()
        ax2.get_legend().remove()

        ax1.set_xlabel(None)
        ax1.set_ylabel(None)
        ax2.set_ylabel(None)

        # Now, let's turn towards the cut-out slanted lines.
        # We create line objects in axes coordinates, in which (0,0), (0,1),
        # (1,0), and (1,1) are the four corners of the axes.
        # The slanted lines themselves are markers at those locations, such that the
        # lines keep their angle and position, independent of the axes size or scale
        # Finally, we need to disable clipping.

        d = .5  # proportion of vertical to horizontal extent of the slanted line
        kwargs = dict(
            marker=[(-1, -d), (1, d)],
            markersize=12,
            linestyle="none",
            color='k',
            mec='k',
            mew=1,
            clip_on=False
        )
        ax1.plot([0, 1], [0, 0], transform=ax1.transAxes, **kwargs)
        ax2.plot([0, 1], [1, 1], transform=ax2.transAxes, **kwargs)

        return ax2

    def heatmap(
        self, data: pd.DataFrame, annot: pd.DataFrame
    ) -> matplotlib.axes.Axes:
        dark_cmap = sns.color_palette('dark').as_hex()
        light_cmap = sns.color_palette('pastel').as_hex()

        cmap = LinearSegmentedColormap.from_list(
            name='test',
            colors=[(0, light_cmap[0]), (0.327, dark_cmap[0]),
                    (0.327777, light_cmap[1]), (0.6666, dark_cmap[1]),
                    (2.0 / 3, light_cmap[2]), (1, dark_cmap[2])]
        )

        ax: matplotlib.axes.Axes = sns.heatmap(
            data,
            annot=annot,
            # fmt='',
            cmap=cmap,
            vmax=3,
        )

        colorbar = ax.collections[0].colorbar
        colorbar.set_ticks([0.5, 1.5, 2.5],
                           labels=[self._get_jf_name(i) for i in range(0, 3)])

        return ax

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        ax = sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            cut=0,
            palette="pastel",
            # inner="point",
        )
        ax.axhline(1)
        ax = sns.stripplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            dodge=True,
            legend=False,
            # color="black"
            # palette='dark:black',
            ax=ax,
        )
        return ax

    def plot(self, view_mode: bool) -> None:
        ax = self.make_phasar_plot()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    @staticmethod
    def compute_speedups(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return list(
            map(
                lambda x: round(x[0] / x[1], 3),
                itertools.product(old_measurements, new_measurements)
            )
        )

    def get_argmaxmin(self, Args: tp.List[float]) -> tp.Tuple[int, int]:
        Max = np.argmax(Args)
        Min = np.argmin(Args)
        return (Max, Min)


class PhasarIterIDEJF1JF2TimeViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-jf1-jf2-time',
    yname="Relative time savings"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3]:
                for time, old_time in zip(
                    aggregates[jf].measurements_wall_clock_time,
                    aggregates[self.OLD].measurements_wall_clock_time
                ):
                    nodes.append({
                        self.YNAME: (old_time - time) / old_time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes


class PhasarIterIDESpeedupVsJF1Plot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-speedup-jf1',
    yname="Runtime Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        # TODO: cross product (see __compute_speedups)
        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3]:
                for s in PhasarIterIDEPlotBase.compute_speedups(
                    aggregates[self.OLD].measurements_wall_clock_time,
                    aggregates[jf].measurements_wall_clock_time
                ):
                    # for time, old_time in zip(
                    #     aggregates[jf].measurements_wall_clock_time,
                    #     aggregates[self.OLD].measurements_wall_clock_time
                    # ):
                    nodes.append({
                        self.YNAME: s,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        ax = sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            cut=0,
            palette="pastel",
            # inner="point",
        )
        ax.axhline(1)
        ax = sns.stripplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            dodge=True,
            legend=False,
            # color="black"
            # palette='dark:black',
            # ax=ax
        )
        # fgrid = sns.catplot(
        #     x="JF",
        #     y=self.YNAME,
        #     data=data,
        #     hue="JF",
        #     col="Analysis",
        # )
        # fgrid.set(ylim=(0,20))
        # ax.set_ylim(top=20)
        return ax


class PhasarIterIDESpeedupHeatmap(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-speedup-heatmap',
    yname="Best Runtime Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)

            Old = aggregates[self.OLD].measurements_wall_clock_time
            JFMeanSpeedups = [
                np.mean(
                    self.compute_speedups(
                        Old, aggregates[jf].measurements_wall_clock_time
                    )
                ) for jf in range(0, 3)
            ]

            MaxSpeedupJF, OtherJF = self.get_argmaxmin(JFMeanSpeedups)

            Weight = 1 - JFMeanSpeedups[OtherJF] / JFMeanSpeedups[MaxSpeedupJF]

            nodes.append({
                self.YNAME: JFMeanSpeedups[MaxSpeedupJF],
                "JF": MaxSpeedupJF,
                "Analysis": ana,
                "Target": cs,
                "WeightedJF": MaxSpeedupJF + Weight,
            })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        # print(f"Data: {data}")
        annot = pd.pivot_table(
            data=data, index="Target", columns="Analysis", values=self.YNAME
        )

        # print(f"Annot: {annot}")
        def last(series):
            return reduce(lambda x, y: y, series)

        # data = pd.pivot_table(data=data,index="Target",columns="Analysis",values="JF", aggfunc=last)
        data = pd.pivot_table(
            data=data,
            index="Target",
            columns="Analysis",
            values="WeightedJF",
            # aggfunc=last,
        )
        print(f"Runtime Data: {data}")

        return self.heatmap(data, annot)


class PhasarIterIDEMemSpeedupHeatmap(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-heatmap',
    yname="Best Memory Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)

            Old = aggregates[self.OLD].max_resident_sizes
            JFMeanSpeedups = [
                np.mean(
                    self.compute_speedups(
                        Old, aggregates[jf].max_resident_sizes
                    )
                ) for jf in range(0, 3)
            ]

            # MaxSpeedupJF = int(np.argmax(JFMeanSpeedups))
            # OtherJF = self.JF2 if MaxSpeedupJF == self.JF1 else self.JF1

            MaxSpeedupJF, OtherJF = self.get_argmaxmin(JFMeanSpeedups)

            Weight = 1 - JFMeanSpeedups[OtherJF] / JFMeanSpeedups[MaxSpeedupJF]

            nodes.append({
                self.YNAME: JFMeanSpeedups[MaxSpeedupJF],
                "JF": MaxSpeedupJF,
                "Analysis": ana,
                "Target": cs,
                "WeightedJF": MaxSpeedupJF + Weight,
            })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        # print(f"Data: {data}")
        annot = pd.pivot_table(
            data=data, index="Target", columns="Analysis", values=self.YNAME
        )

        # print(f"Annot: {annot}")
        def last(series):
            return reduce(lambda x, y: y, series)

        data = pd.pivot_table(
            data=data,
            index="Target",
            columns="Analysis",
            values="WeightedJF",
            # aggfunc=last,
        )
        print(f"Memory Data: {data}")

        return self.heatmap(data, annot)


class PhasarIterIDENewTime(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-new-time',
    yname="Runtime [s]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3]:
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        self.YNAME: time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        ax = sns.boxplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            showfliers=False,
        )
        ax.set_ylim(top=600)
        return ax


class PhasarIterIDEMemSpeedupVsJF1Plot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-jf1',
    yname="Memory Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3]:
                for s in PhasarIterIDEPlotBase.compute_speedups(
                    aggregates[self.OLD].max_resident_sizes,
                    aggregates[jf].max_resident_sizes
                ):
                    # for mem, old_mem in zip(
                    #     aggregates[jf].max_resident_sizes,
                    #     aggregates[self.JF1].max_resident_sizes
                    # ):
                    nodes.append({
                        self.YNAME: s,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    # def make_phasar_plot(self) -> matplotlib.axes.Axes:
    #     data = self.make_dataframe()
    #     ax = sns.boxplot(
    #         x="Analysis",
    #         y=self.YNAME,
    #         data=data,
    #         hue="JF",
    #     )
    #     ax.set_ylim(bottom=-7500)
    #     return ax


class PhasarIterIDENewMem(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-new-mem',
    yname="Memory [MB]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3]:
                for mem in aggregates[jf].max_resident_sizes:
                    nodes.append({
                        self.YNAME: mem / 1000,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        ax = sns.boxplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            showfliers=False,
        )
        ax.set_ylim(top=15000)
        return ax


class PhasarIterIDEOldNewMemViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-old-new-mem',
    yname="Max Resident Size [MB]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3, self.OLD]:
                for mem, old_mem in zip(
                    aggregates[jf].max_resident_sizes,
                    aggregates[self.OLD].max_resident_sizes
                ):
                    nodes.append({
                        self.YNAME: mem / 1000,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        return self.broken_boxplot(
            data, [1, 2], [15000, 0, 2500], [100000, 55000, 10000]
        )


class PhasarIterIDEOldNewTimeViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-old-new-time',
    yname="Runtime [s]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(self, report: PhasarIterIDEStatsReport,
                          cs: str) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [0, 1, 2, 3]:
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        self.YNAME: time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        return self.broken_boxplot(
            data, [1, 2], [500, 0, 60], [4000, 2250, 500]
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CAIGViolinPlotGenerator(
    PlotGenerator, generator_name="phasar-iter-ide-jf1-jf2", options=[]
):
    """Generates a violin plot showing the distribution of interacting authors
    for each case study."""

    def generate(self) -> tp.List[Plot]:
        return [
            PhasarIterIDEJF1JF2TimeViolinPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEOldNewTimeViolinPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEOldNewMemViolinPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDESpeedupVsJF1Plot(self.plot_config, **self.plot_kwargs),
            PhasarIterIDEMemSpeedupVsJF1Plot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDENewTime(self.plot_config, **self.plot_kwargs),
            PhasarIterIDENewMem(self.plot_config, **self.plot_kwargs),
            PhasarIterIDESpeedupHeatmap(self.plot_config, **self.plot_kwargs),
            PhasarIterIDEMemSpeedupHeatmap(
                self.plot_config, **self.plot_kwargs
            ),
        ]

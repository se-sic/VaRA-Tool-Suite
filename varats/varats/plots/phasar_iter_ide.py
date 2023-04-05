"""Module for BlameInteractionGraph plots."""

import abc
import typing as tp
from math import ceil, floor

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
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

    JF2 = 0
    JF1 = 1
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
                report.new_taint, report.new_taint_jf1, report.new_taint_jf3,
                report.old_taint
            ]
        elif ana == self.TYPESTATE:
            return [
                report.new_typestate, report.new_typestate_jf1,
                report.new_typestate_jf3, report.old_typestate
            ]
        elif ana == self.LCA:
            return [
                report.new_lca, report.new_lca_jf1, report.new_lca_jf3,
                report.old_lca
            ]
        else:
            raise "ERROR: Invalid analysis: " + ana

    @abc.abstractmethod
    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        pass

    def _get_jf_name(self, jf: int) -> str:
        if jf == self.JF1:
            return "JF1"
        elif jf == self.JF2:
            return "JF2"
        elif jf == self.JF3:
            return "JF3"
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
                nodes.extend(self._get_data_entries(report))

        return pd.DataFrame(nodes).sort_values(by=["Analysis", "JF"])

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()
        return sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
        )

    def plot(self, view_mode: bool) -> None:
        ax = self.make_phasar_plot()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PhasarIterIDEJF1JF2TimeViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-jf1-jf2-time',
    yname="Relative time savings"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport
    ) -> tp.List[tp.Dict[str, tp.Any]]:
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


class PhasarIterIDEJF1JF2MemViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-jf1-jf2-mem',
    yname="Max Resident Size (MB)"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport
    ) -> tp.List[tp.Dict[str, tp.Any]]:
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

        # See: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/broken_axis.html
        #
        # If we were to simply plot pts, we'd lose most of the interesting
        # details due to the outliers. So let's 'break' or 'cut-out' the y-axis
        # into two portions - use the top (ax1) for the outliers, and the bottom
        # (ax2) for the details of the majority of our data

        # fig, (ax1, ax2) = matplotlib.pyplot.subplots(2, 1, sharex = True)

        fig = plt.figure()

        gs = GridSpec(2, 2, height_ratios=[1, 2])

        ax1 = fig.add_subplot(gs.new_subplotspec((0, 0), colspan=2))
        ax2 = fig.add_subplot(gs.new_subplotspec((1, 0), colspan=2))

        fig.subplots_adjust(hspace=0.1)  # adjust space between axes
        fig.text(0.02, 0.5, self.YNAME, va="center", rotation="vertical")

        ax1.set_yticks(np.arange(0, 100000, 10000))
        ax2.set_yticks(np.arange(0, 100000, 2500))

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
        ax1.set_ylim(top=100000, bottom=55000)  # outliers only
        ax2.set_ylim(top=15000, bottom=0)  # most of the data

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

        return ax1


class PhasarIterIDEOldNewTimeViolinPlot(
    PhasarIterIDEPlotBase, plot_name='phasar-iter-ide-old-new-time'
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [0, 1, 2, 3]:
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        "Time": time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe()

        # See: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/broken_axis.html
        #
        # If we were to simply plot pts, we'd lose most of the interesting
        # details due to the outliers. So let's 'break' or 'cut-out' the y-axis
        # into two portions - use the top (ax1) for the outliers, and the bottom
        # (ax2) for the details of the majority of our data

        # fig, (ax1, ax2) = matplotlib.pyplot.subplots(2, 1, sharex = True)

        fig = plt.figure()

        gs = GridSpec(2, 2, height_ratios=[1, 2])

        ax1 = fig.add_subplot(gs.new_subplotspec((0, 0), colspan=2))
        ax2 = fig.add_subplot(gs.new_subplotspec((1, 0), colspan=2))

        fig.subplots_adjust(hspace=0.1)  # adjust space between axes
        fig.text(0.02, 0.5, self.YNAME, va="center", rotation="vertical")

        ax1.set_yticks(np.arange(0, 4000, 500))
        ax2.set_yticks(np.arange(0, 4000, 100))

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
        ax1.set_ylim(top=4000, bottom=2000)  # outliers only
        ax2.set_ylim(top=400, bottom=0)  # most of the data

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
            PhasarIterIDEJF1JF2MemViolinPlot(
                self.plot_config, **self.plot_kwargs
            ),
        ]

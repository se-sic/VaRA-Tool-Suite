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
from matplotlib.markers import MarkerStyle, JoinStyle
from matplotlib.ticker import Locator, FixedLocator, StrMethodFormatter

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    create_file_based_interaction_graph,
    AIGNodeAttrs,
    create_callgraph_based_interaction_graph,
)
from varats.data.reports.phasar_iter_ide import (
    PhasarIterIDEStatsReport,
    merge_dict,
)
from varats.experiments.phasar.iter_ide import (
    IDELinearConstantAnalysisExperiment,
    IDELinearConstantAnalysisExperimentWL,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.experiments.vara.iter_ide_br_iia import IterIDEBlameReportExperiment
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
from varats.utils.git_util import FullCommitHash, calc_repo_loc


def from_kibytes_to_mibytes(kbytes: float) -> float:
    return kbytes / 1024.


class PhasarIterIDEPlotBase(Plot, plot_name="phasar-iter-ide-plot"):
    YNAME = "Time"

    TAINT = "Taint"
    TYPESTATE = "Typestate"
    LCA = "LCA"
    IIA = "IIA"

    JF1 = 0
    JF2 = 1
    JF3 = 2
    Nested = 3
    OLD = 4

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
                report.new_taint_nested, report.old_taint
            ]
        elif ana == self.TYPESTATE:
            return [
                report.new_typestate_jf1, report.new_typestate,
                report.new_typestate_jf3, report.new_typestate_nested,
                report.old_typestate
            ]
        elif ana == self.LCA:
            return [
                report.new_lca_jf1, report.new_lca, report.new_lca_jf3,
                report.new_lca_nested, report.old_lca
            ]
        elif ana == self.IIA:
            return [
                report.new_iia_jf1, report.new_iia, report.new_iia_jf3,
                report.new_iia_nested, report.old_iia
            ]
        else:
            raise "ERROR: Invalid analysis: " + ana

    def _get_gc_aggregates(self, report: PhasarIterIDEStatsReport,
                           ana: str) -> tp.List[TimeReportAggregate]:
        if ana == self.TAINT:
            return [
                report.new_taint_gc_jf1, report.new_taint_gc,
                report.new_taint_jf3, report.new_taint_nested, report.old_taint
            ]
        elif ana == self.TYPESTATE:
            return [
                report.new_typestate_gc_jf1, report.new_typestate_gc,
                report.new_typestate_jf3, report.new_typestate_nested,
                report.old_typestate
            ]
        elif ana == self.LCA:
            return [
                report.new_lca_gc_jf1, report.new_lca_gc, report.new_lca_jf3,
                report.new_lca_nested, report.old_lca
            ]
        elif ana == self.IIA:
            return [
                report.new_iia_gc_jf1, report.new_iia_gc, report.new_iia_jf3,
                report.new_iia_nested, report.old_iia
            ]
        else:
            raise "ERROR: Invalid analysis: " + ana

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

    @staticmethod
    def compute_mean_speedup(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return [
            np.mean(
                list(
                    map(
                        lambda x: round(x[0] / x[1], 3),
                        itertools.product(old_measurements, new_measurements)
                    )
                )
            )
        ]

    @abc.abstractmethod
    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        pass

    def _get_jf_name(self, jf: int) -> str:
        if jf == self.JF1:
            return "JF1"
        elif jf == self.JF2:
            return "JF4"
        elif jf == self.JF3:
            return "JF4S"
        elif jf == self.Nested:
            return "Nested"
        elif jf == self.OLD:
            return "Old"
        else:
            raise "ERROR: Table Rep out-of-range: " + str(jf)

    def make_dataframe(
        self, speedup_computer: tp.Callable[[tp.List[float], tp.List[float]],
                                            float]
    ) -> pd.DataFrame:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        timeouts = dict()
        ooms = dict()
        for case_study in case_studies:
            project_name = case_study.project_name
            # loc = 42

            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

            assert len(
                report_files
            ) <= 1, f"Invalid length of report_files list: got {len(report_files)}, expected 1"

            iia_report_files = get_processed_revisions_files(
                case_study.project_name, IterIDEBlameReportExperiment,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

            assert len(iia_report_files) <= 1

            if (len(report_files) == 0 and len(iia_report_files) == 0):
                continue

            print("Num Reports: ", len(report_files))

            for report_file, iia_report_file in itertools.zip_longest(
                report_files, iia_report_files
            ):
                # print("Report: ", report_file)
                report = load_phasar_iter_ide_stats_report(
                    report_file
                ) if report_file is not None else None
                iia_report = load_phasar_iter_ide_stats_report(
                    iia_report_file
                ) if iia_report_file is not None else None
                # print(iia_report)
                if report is None:
                    # print("Have IIA report, but no regular report")
                    report = iia_report
                elif not (iia_report is None):
                    # print("Have both reports")
                    report.merge_with(iia_report)
                # else:
                #     print("Have only regular report")

                local_timeouts = report.aggregate_timeouts()
                merge_dict(timeouts, local_timeouts, lambda x, y: x + y)

                local_ooms = report.aggregate_ooms()
                merge_dict(ooms, local_ooms, lambda x, y: x + y)

                entries = self._get_data_entries(
                    report, project_name, speedup_computer
                )

                for entry in entries:
                    entry["LOC"] = report.basic_bc_stats.num_instructions
                    entry["Target"] = project_name
                    nodes.append(entry)

        print("Timeouts: ", timeouts)
        print("OOMs: ", ooms)
        df = pd.DataFrame(nodes)
        # print("DataFrame: ", df)
        return df.sort_values(by=["Analysis", "JF"])

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

        fig, ax = plt.subplots(figsize=(3.5, 4))

        sns.heatmap(
            data,
            annot=annot,
            fmt=".1f",
            cmap=cmap,
            vmax=3,
            ax=ax,
        )

        colorbar = ax.collections[0].colorbar
        colorbar.set_ticks([0.5, 1.5, 2.5],
                           labels=[self._get_jf_name(i) for i in range(0, 3)])

        return ax

    def data_point_threshold(self) -> int:
        return 100

    def analysis_order(self) -> tp.List[str]:
        return ["IIA", "LCA", "Taint", "Typestate"]

    def make_phasar_violinplot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(self.compute_speedups)
        ax = sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            cut=0,
            palette="pastel",
            order=self.analysis_order(),
            # inner="point",
        )
        ax.axhline(1)

        data = self.make_dataframe(self.compute_mean_speedup)

        # print(f"make_phasar_plot: {data}")
        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"{ana}: Min {Min}, Max {Max}, Mean {Mean}")

        # threshold = self.data_point_threshold()
        threshold = 0
        # gray_data = data.loc[data["Old"] < threshold]
        colored_data = data if threshold == 0 else data.loc[
            data["Old"] >= threshold]

        # print(f"make_phasar_plot: {gray_data}")

        ax = sns.stripplot(
            x="Analysis",
            y=self.YNAME,
            data=colored_data,
            hue="JF",
            dodge=True,
            legend=False,
            jitter=True,
            marker='x',
            edgecolor='face',
            linewidth=1,
            # ax=ax,
            order=self.analysis_order(),
        )

        # ax= sns.stripplot(
        #     x="Analysis",
        #     y=self.YNAME,
        #     data=gray_data,
        #     hue="JF",
        #     dodge=True,
        #     legend=False,
        #     jitter=True,
        #     marker='x',
        #     # edgecolor='face',
        #     facecolor='lightgray',
        #     linewidth=1,
        #     #ax=ax,
        #     order=["IIA", "LCA", "Taint", "Typestate"],
        # )

        return ax

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        ax = self.make_phasar_violinplot()
        ax.axhline(1)
        return ax

    def plot(self, view_mode: bool) -> None:
        ax = self.make_phasar_plot()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def get_argmaxmin(self, Args: tp.List[float]) -> tp.Tuple[int, int]:
        Max = np.argmax(Args)
        Min = np.argmin(Args)
        return (Max, Min)


class PhasarIterIDERuntimeSpeedupPlotBase(PhasarIterIDEPlotBase, plot_name=""):

    def __init_subclass__(
        cls,
        *,
        plot_name: tp.Optional[str],
        yname: tp.Optional[str] = None,
        **kwargs: tp.Any
    ) -> None:
        return super().__init_subclass__(
            plot_name=plot_name, yname=yname, **kwargs
        )

    def data_point_threshold(self) -> int:
        return 5

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                print(f"Skip {ana}")
                continue
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested]:
                if aggregates[jf] is None:
                    print(f"Skip {self._get_jf_name(jf)} for {ana}")
                    continue
                for s in speedup_computer(
                    aggregates[self.OLD].measurements_wall_clock_time,
                    aggregates[jf].measurements_wall_clock_time
                ):
                    # print(f"> {s}")
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            np.mean(
                                aggregates[self.OLD
                                          ].measurements_wall_clock_time
                            ),
                        "New":
                            np.mean(
                                aggregates[jf].measurements_wall_clock_time
                            ),
                        "Target":
                            cs,
                    })

        return nodes


class PhasarIterIDECombinedSpeedupPlotBase(PhasarIterIDEPlotBase, plot_name=""):

    def __init_subclass__(
        cls,
        *,
        plot_name: tp.Optional[str],
        yname: tp.Optional[str] = None,
        **kwargs: tp.Any
    ) -> None:
        return super().__init_subclass__(
            plot_name=plot_name, yname=yname, **kwargs
        )

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.Nested] is None:
                print(f"Skip {ana}")
                continue
            for jf in [self.JF1, self.JF2, self.JF3]:
                if aggregates[jf] is None:
                    print(f"Skip {self._get_jf_name(jf)} for {ana}")
                    continue

                runtime_speedups = speedup_computer(
                    aggregates[self.Nested].measurements_wall_clock_time,
                    aggregates[jf].measurements_wall_clock_time
                )

                memory_speedups = speedup_computer(
                    aggregates[self.Nested].max_resident_sizes,
                    aggregates[jf].max_resident_sizes
                )

                for s, m in zip(runtime_speedups, memory_speedups):
                    # print(f"> {s}")
                    nodes.append({
                        "Runtime Speedup":
                            s,
                        "Memory Savings":
                            m,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Target":
                            cs,
                        "Old Runtime":
                            np.mean(
                                aggregates[self.Nested
                                          ].measurements_wall_clock_time
                            ),
                        "New Runtime":
                            np.mean(
                                aggregates[jf].measurements_wall_clock_time
                            ),
                        "Old Memory":
                            from_kibytes_to_mibytes(
                                np.mean(
                                    aggregates[self.Nested].max_resident_sizes
                                )
                            ),
                        "New Memory":
                            from_kibytes_to_mibytes(
                                np.mean(aggregates[jf].max_resident_sizes)
                            ),
                    })

        return nodes


class PhasarIterIDEMemorySpeedupPlotBase(PhasarIterIDEPlotBase, plot_name=""):

    def __init_subclass__(
        cls,
        *,
        plot_name: tp.Optional[str],
        yname: tp.Optional[str] = None,
        **kwargs: tp.Any
    ) -> None:
        return super().__init_subclass__(
            plot_name=plot_name, yname=yname, **kwargs
        )

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                continue
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested]:
                if aggregates[jf] is None:
                    continue
                for s in speedup_computer(
                    aggregates[self.OLD].max_resident_sizes,
                    aggregates[jf].max_resident_sizes
                ):
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            from_kibytes_to_mibytes(
                                np.mean(
                                    aggregates[self.OLD].max_resident_sizes
                                )
                            ),
                        "New":
                            from_kibytes_to_mibytes(
                                np.mean(aggregates[jf].max_resident_sizes)
                            ),
                        "Target":
                            cs,
                    })

        return nodes


class PhasarIterIDESpeedupJFvsNestedPlotBase(
    PhasarIterIDERuntimeSpeedupPlotBase,
    plot_name='phasar-iter-ide-speedup-jf-vs-nested',
    yname="Runtime Speedup vs Nested"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.Nested] is None:
                print(f"Skip {ana}")
                continue

            for jf in [self.JF1, self.JF2, self.JF3]:
                if aggregates[jf] is None:
                    print(f"Skip {self._get_jf_name(jf)} for {ana}")
                    continue
                for s in speedup_computer(
                    aggregates[self.Nested].measurements_wall_clock_time,
                    aggregates[jf].measurements_wall_clock_time
                ):
                    # print(f"> {s}")
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            np.mean(
                                aggregates[self.Nested
                                          ].measurements_wall_clock_time
                            ),
                        "New":
                            np.mean(
                                aggregates[jf].measurements_wall_clock_time
                            ),
                        "Target":
                            cs,
                    })

        return nodes


class PhasarIterIDEMemSpeedupJFvsNestedPlotBase(
    PhasarIterIDEMemorySpeedupPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-jf-vs-nested',
    yname="Memory Savings vs Nested"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.Nested] is None:
                continue
            for jf in [self.JF1, self.JF2, self.JF3]:
                if aggregates[jf] is None:
                    continue
                for s in speedup_computer(
                    aggregates[self.Nested].max_resident_sizes,
                    aggregates[jf].max_resident_sizes
                ):
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            from_kibytes_to_mibytes(
                                np.mean(
                                    aggregates[self.Nested].max_resident_sizes
                                )
                            ),
                        "New":
                            from_kibytes_to_mibytes(
                                np.mean(aggregates[jf].max_resident_sizes)
                            ),
                        "Target":
                            cs,
                    })

        return nodes


################################################################################
#                         Concrete Implementations                             #
################################################################################


class PhasarIterIDESpeedupVsJF1Plot(
    PhasarIterIDERuntimeSpeedupPlotBase,
    plot_name='phasar-iter-ide-speedup-jf1',
    yname="Runtime Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""


class PhasarIterIDEMemSpeedupVsJF1Plot(
    PhasarIterIDEMemorySpeedupPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-jf1',
    yname="Memory Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""


class PhasarIterIDESpeedupJFvsNested(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-speedup-jf-vs-nested',
    yname="Runtime Speedup vs Nested"
):
    pass


class PhasarIterIDETargetSpeedupVsNested(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-speedup-target-scatter-vs-nested',
    yname="Runtime Speedup vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        for ana in ["Taint", "LCA", "IIA"]:
            Rows = data.loc[data["Analysis"] == ana][self.YNAME]
            Min = Rows.min()
            Max = Rows.max()
            Mean = Rows.mean()
            print(
                f"[PhasarIterIDETargetSpeedupVsNested]: {ana}: Min {Min}, Max {Max}, Mean {Mean}"
            )

        # print("Dataset: ", data.to_string())

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDETargetSpeedupVsNestedSortedSize(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-speedup-target-scatter-vs-nested-sorted-size',
    yname="Runtime Speedup vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)
        data = data.sort_values(by=["LOC"])

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            hue_order=["JF1", "JF4", "JF4S"],
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))

        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDETargetSpeedupVsNestedSortedTime(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-speedup-target-scatter-vs-nested-sorted-time',
    yname="Runtime Speedup vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)
        data = data.sort_values(by=["Old"])

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            hue_order=["JF1", "JF4", "JF4S"],
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDELineTargetSpeedupVsNested(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-speedup-target-line-vs-nested',
    yname="Runtime Speedup vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        data = data.sort_values(by=[self.YNAME, "JF"])

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDESpeedupTargetScatter]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        # print("Dataset: ", data.to_string())

        ax = sns.lineplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            hue_order=["JF1", "JF4", "JF4S"],
            units="Analysis",
            style="Analysis",
            # linewidth=0,
            # alpha=0.7,
            estimator=None,
            lw=1,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )

        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))

        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDEAbsoluteSpeedupJFvsNested(
    PhasarIterIDESpeedupJFvsNested,
    plot_name='phasar-iter-ide-abs-speedup-jf-vs-nested',
    yname="Runtime Speedup vs Nested [s]"
):

    @staticmethod
    def compute_speedups(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return list(
            map(
                lambda x: round(x[0] - x[1], 3),
                itertools.product(old_measurements, new_measurements)
            )
        )

    @staticmethod
    def compute_mean_speedup(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return [
            np.mean(
                list(
                    map(
                        lambda x: round(x[0] - x[1], 3),
                        itertools.product(old_measurements, new_measurements)
                    )
                )
            )
        ]

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(self.compute_speedups)
        ax = sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            cut=0,
            palette="pastel",
            # inner="point",
        )
        ax.axhline(0)

        data = self.make_dataframe(self.compute_mean_speedup)

        # print(f"make_phasar_plot: {data}")
        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"{ana}: Min {Min}, Max {Max}, Mean {Mean}")

        ax = sns.stripplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            dodge=True,
            legend=False,
            jitter=True,
            marker='x',
            edgecolor='face',
            linewidth=1,
            ax=ax,
        )
        return ax


class PhasarIterIDEMemSpeedupJFvsNested(
    PhasarIterIDEMemSpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-jf-vs-nested',
    yname="Memory Savings vs Nested"
):
    pass


class PhasarIterIDETargetMemSpeedupVsNested(
    PhasarIterIDEMemSpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-target-scatter-vs-nested',
    yname="Memory Savings vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        for ana in ["Taint", "LCA", "IIA"]:
            Rows = data.loc[data["Analysis"] == ana][self.YNAME]
            Min = Rows.min()
            Max = Rows.max()
            Mean = Rows.mean()
            print(
                f"[PhasarIterIDETargetMemSpeedupVsNested]: {ana}: Min {Min}, Max {Max}, Mean {Mean}"
            )

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Memory Savings")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDETargetMemSpeedupVsNestedSortedSize(
    PhasarIterIDEMemSpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-target-scatter-vs-nested-sorted-size',
    yname="Memory Savings vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)
        data = data.sort_values(by=["LOC"])

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            hue_order=["JF1", "JF4", "JF4S"],
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Memory Savings")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDETargetMemSpeedupVsNestedSortedMem(
    PhasarIterIDEMemSpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-target-scatter-vs-nested-sorted-mem',
    yname="Memory Savings vs Nested"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)
        data = data.sort_values(by=["Old"])

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            hue_order=["JF1", "JF4", "JF4S"],
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Memory Savings")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDEGrid(
    PhasarIterIDESpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-grid',
    yname="Runtime Speedup"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDETargetMemSpeedupVsNested]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        ax = sns.displot(
            data=data,
            x="JF",
            y=self.YNAME,
            col="Analysis",
            col_wrap=2,
            #height = 4,
            #aspect = 0.7,
        )

        return ax


class PhasarIterIDEMemGrid(
    PhasarIterIDEMemSpeedupJFvsNestedPlotBase,
    plot_name='phasar-iter-ide-mem-grid',
    yname="Memory Savings"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDETargetMemSpeedupVsNested]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        ax = sns.displot(
            data=data,
            x="JF",
            y=self.YNAME,
            col="Analysis",
            col_wrap=2,
            #height = 4,
            #aspect = 0.7,
        )

        return ax


class PhasarIterIDEAbsoluteMemSpeedupJFvsNested(
    PhasarIterIDEMemSpeedupJFvsNested,
    plot_name='phasar-iter-ide-abs-mem-speedup-jf-vs-nested',
    yname="Memory Savings vs Nested [MiB]"
):

    @staticmethod
    def compute_speedups(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return list(
            map(
                lambda x: from_kibytes_to_mibytes(round(x[0] - x[1], 3)),
                itertools.product(old_measurements, new_measurements)
            )
        )

    @staticmethod
    def compute_mean_speedup(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return [
            np.mean(
                list(
                    map(
                        lambda x:
                        from_kibytes_to_mibytes(round(x[0] - x[1], 3)),
                        itertools.product(old_measurements, new_measurements)
                    )
                )
            )
        ]

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(self.compute_speedups)
        ax = sns.violinplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            cut=0,
            palette="pastel",
            # inner="point",
        )
        ax.axhline(0)

        data = self.make_dataframe(self.compute_mean_speedup)

        # print(f"make_phasar_plot: {data}")
        for ana in ["Taint", "LCA", "IIA"]:
            Rows = data.loc[data["Analysis"] == ana][self.YNAME]
            Min = Rows.min()
            Max = Rows.max()
            Mean = Rows.mean()
            print(f"{ana}: Min {Min}, Max {Max}, Mean {Mean}")

        ax = sns.stripplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            dodge=True,
            legend=False,
            jitter=True,
            marker='x',
            edgecolor='face',
            linewidth=1,
            ax=ax,
        )
        return ax


class PhasarIterIDECombinedSpeedupPlot(
    PhasarIterIDECombinedSpeedupPlotBase,
    plot_name='phasar-iter-ide-combined-speedup',
    yname="Speedup vs Nested"
):

    @staticmethod
    def compute_single_sanitized_speedup(old: float, new: float) -> float:

        # return round((old - new) / old, 3) * 100

        if old < new:
            return -round(new / old - 1, 3)
        else:
            return round(old / new - 1, 3)

        # if old < new:
        #     return -round(new/old, 3)
        # else:
        #     return round(old/new, 3)

    @staticmethod
    def compute_sanitized_speedup(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return [
            np.mean(
                list(
                    map(
                        lambda x: PhasarIterIDECombinedSpeedupPlot.
                        compute_single_sanitized_speedup(x[0], x[1]),
                        itertools.product(old_measurements, new_measurements)
                    )
                )
            )
        ]

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(
            PhasarIterIDECombinedSpeedupPlot.compute_sanitized_speedup
        )

        runtime_threshold = 5
        memory_threshold = 100

        gray_data = data.loc[(data["Old Runtime"] < runtime_threshold) &
                             (data["Old Memory"] < memory_threshold) &
                             (data["New Runtime"] < runtime_threshold) &
                             (data["New Memory"] < memory_threshold)]
        colored_data = data.loc[(data["Old Runtime"] >= runtime_threshold) |
                                (data["Old Memory"] >= memory_threshold) |
                                (data["New Runtime"] >= runtime_threshold) |
                                (data["New Memory"] >= memory_threshold)]

        #print(data)

        ax = sns.scatterplot(
            data=gray_data,
            x="Runtime Speedup",
            y="Memory Savings",
            # x = "Old",
            # y = "New",
            # hue="Target",
            hue="JF",
            # markers = markers,
            # fillstyle="none",
            # facecolors="none",
            # edgecolor="face",
            # c='none',
            facecolor='lightgray',
            linewidth=0,
            alpha=0.5,
            # s=25,
            legend=False,
        )

        ax = sns.scatterplot(
            data=colored_data,
            x="Runtime Speedup",
            y="Memory Savings",
            # x = "Old",
            # y = "New",
            style="Target",
            hue="JF",
            # markers = markers,
            # fillstyle="none",
            # facecolors="none",
            # edgecolor="face",
            # c='none',
            linewidth=0,
            alpha=0.5,
            # s=25,
        )

        # Move left y-axis and bottom x-axis to centre, passing through (0,0)
        ax.spines['left'].set_position('zero')
        ax.spines['bottom'].set_position('zero')

        # Eliminate upper and right axes
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')

        # Show ticks in the left and lower axes only
        ax.xaxis.set_ticks_position('bottom')
        ax.yaxis.set_ticks_position('left')

        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))

        # ax.set_yticks(
        #     [
        #        -4, -2, #-1,
        #         *np.arange(
        #             2, 15, 2
        #         ),
        #     ]
        # )
        # ax.set_xticks(
        #     [   -4,
        #         -2,
        #         #-1,
        #         *np.arange(
        #             2, 10, 2
        #         ),
        #         *np.arange(
        #             10, 27, 4
        #         ),
        #     ]
        # )

        # unit_circle = plt.Circle((0, 0), 1, fill=False)
        # ax.add_patch(unit_circle)

        #ax.set_aspect('equal', adjustable='box')

        # ax.set_xscale('log')
        # ax.set_yscale('log')

        # ax.axline(xy1=(0, 0), slope=1)

        ax.set_xlabel("Runtime Speedup")
        ax.set_ylabel("Memory Savings")

        return ax


class PhasarIterIDESpeedupScatterPlot(
    PhasarIterIDERuntimeSpeedupPlotBase,
    plot_name='phasar-iter-ide-speedup-scatter',
    yname="Runtime Old vs New [s]"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # print(data.to_string())
        # data = data.loc[data["Analysis"] == "Taint"]

        # markers = ['x', (5, 2),  matplotlib.markers.MarkerStyle("s", fillstyle="none")]
        # markers = ['X', '^', (5, 1)]
        # markers = [
        #     matplotlib.markers.MarkerStyle("X", fillstyle="none"),
        #     matplotlib.markers.MarkerStyle("o", fillstyle="none"),
        #     matplotlib.markers.MarkerStyle("*", fillstyle="none"),
        #    # matplotlib.markers.MarkerStyle("s", fillstyle="none")
        # ]

        ax = sns.scatterplot(
            data=data,
            x="New",
            y="Old",
            # x = "Old",
            # y = "New",
            hue="Target",
            style="JF",
            # markers = markers,
            # fillstyle="none",
            # facecolors="none",
            # edgecolor="face",
            # c='none',
            linewidth=0,
            alpha=0.5,
            # s=25,
        )

        ax.axline(xy1=(0, 0), slope=1)

        ax.set_ylabel("Old Runtime [s]")
        ax.set_xlabel("New Runtime [s]")
        # ax.set_yscale('log')

        return ax


class PhasarIterIDEOldNewNestedScatterPlot(
    PhasarIterIDERuntimeSpeedupPlotBase,
    plot_name='phasar-iter-ide-speedup-scatter-old-new-nested',
    yname="Runtime Old vs New [s]"
):

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                print(f"Skip {ana}")
                continue

            jf = self.Nested

            if aggregates[jf] is None:
                print(f"Skip {self._get_jf_name(jf)} for {ana}")
                continue
            for s in speedup_computer(
                aggregates[self.OLD].measurements_wall_clock_time,
                aggregates[jf].measurements_wall_clock_time
            ):
                # print(f"> {s}")
                nodes.append({
                    self.YNAME:
                        s,
                    "JF":
                        self._get_jf_name(jf),
                    "Analysis":
                        ana,
                    "Old":
                        np.mean(
                            aggregates[self.OLD].measurements_wall_clock_time
                        ),
                    "New":
                        np.mean(aggregates[jf].measurements_wall_clock_time),
                    "Target":
                        cs,
                })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        ax = sns.scatterplot(
            data=data,
            x="New",
            y="Old",
            # x = "Old",
            # y = "New",
            hue="Target",
            # style="JF",
            # markers = 'x',
            # fillstyle="none",
            # facecolors="none",
            # edgecolor="face",
            # c='none',
            linewidth=0,
            alpha=0.8,
            # s=25,
        )

        ax.axline(xy1=(0, 0), slope=1)

        ax.set_ylabel("Old Runtime [s]")
        ax.set_xlabel("New Runtime [s]")
        # ax.set_yscale('log')

        return ax


class PhasarIterIDEMemOldNewNestedScatterPlot(
    PhasarIterIDEMemorySpeedupPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-scatter-old-new-nested',
    yname="Memory Old vs New [s]"
):

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                print(f"Skip {ana}")
                continue

            jf = self.Nested

            if aggregates[jf] is None:
                print(f"Skip {self._get_jf_name(jf)} for {ana}")
                continue
            for s in speedup_computer(
                aggregates[self.OLD].max_resident_sizes,
                aggregates[jf].max_resident_sizes
            ):
                # print(f"> {s}")
                nodes.append({
                    self.YNAME:
                        s,
                    "JF":
                        self._get_jf_name(jf),
                    "Analysis":
                        ana,
                    "Old":
                        from_kibytes_to_mibytes(
                            np.mean(aggregates[self.OLD].max_resident_sizes)
                        ),
                    "New":
                        from_kibytes_to_mibytes(
                            np.mean(aggregates[jf].max_resident_sizes)
                        ),
                    "Target":
                        cs,
                })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        ax = sns.scatterplot(
            data=data,
            x="New",
            y="Old",
            # x = "Old",
            # y = "New",
            hue="Target",
            # style="JF",
            # markers = 'x',
            # fillstyle="none",
            # facecolors="none",
            # edgecolor="face",
            # c='none',
            linewidth=0,
            alpha=0.8,
            # s=25,
        )

        ax.axline(xy1=(0, 0), slope=1)

        ax.set_ylabel("Old Memory [MiB]")
        ax.set_xlabel("New Memory [MiB]")
        # ax.set_yscale('log')

        return ax


class PhasarIterIDESpeedupTargetScatter(
    PhasarIterIDERuntimeSpeedupPlotBase,
    plot_name='phasar-iter-ide-speedup-target-scatter',
    yname="Runtime Old vs New [s]"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDESpeedupTargetScatter]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        # print("Dataset: ", data.to_string())

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDEMemSpeedupScatterPlot(
    PhasarIterIDEMemorySpeedupPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-scatter',
    yname="Memory Old vs New [MiB]"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # data = data.loc[data["Analysis"] == "Taint"]
        # markers = ['X', '^', (5, 1)]

        ax = sns.scatterplot(
            data=data,
            x="New",
            y="Old",
            # x = "Old",
            # y = "New",
            hue="Target",
            style="JF",
            linewidth=0,
            #s=30,
            #markers=markers,
            alpha=0.5,
        )

        ax.axline(xy1=(0, 0), slope=1)

        ax.set_ylabel("Old Memory [MiB]")
        ax.set_xlabel("New Memory [MiB]")
        # ax.set_yscale('log')

        return ax


class PhasarIterIDEMemSpeedupTargetScatter(
    PhasarIterIDEMemorySpeedupPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-target-scatter',
    yname="Memory Old vs New [s]"
):

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        for ana in ["Taint", "LCA", "IIA"]:
            Rows = data.loc[data["Analysis"] == ana][self.YNAME]
            Min = Rows.min()
            Max = Rows.max()
            Mean = Rows.mean()
            print(
                f"[PhasarIterIDESpeedupTargetScatter]: {ana}: Min {Min}, Max {Max}, Mean {Mean}"
            )

        # print("Dataset: ", data.to_string())

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Memory Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDESpeedupGCPlotBase(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-speedup-gc-plot-base',
    yname="Runtime Speedup /w GC"
):

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            gc_aggregates = self._get_gc_aggregates(report, ana)

            for jf in [self.JF1, self.JF2]:
                speedups = [
                    float('nan')
                ] if aggregates[jf] is None or gc_aggregates[
                    jf] is None else speedup_computer(
                        aggregates[jf].measurements_wall_clock_time,
                        gc_aggregates[jf].measurements_wall_clock_time
                    )

                for s in speedups:
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            np.mean(
                                aggregates[jf].measurements_wall_clock_time
                            ),
                        "New":
                            np.mean(
                                gc_aggregates[jf].measurements_wall_clock_time
                            ),
                    })

        return nodes


class PhasarIterIDESpeedupGCPlot(
    PhasarIterIDESpeedupGCPlotBase,
    plot_name='phasar-iter-ide-speedup-gc',
    yname="Runtime Speedup /w GC"
):
    """Box plot of commit-author interaction commit node degrees."""

    def analysis_order(self) -> tp.List[str]:
        return ["LCA", "Taint", "Typestate"]


class PhasarIterIDESpeedupGCScatterPlot(
    PhasarIterIDESpeedupGCPlotBase,
    plot_name='phasar-iter-ide-speedup-scatter-gc',
    yname="Runtime Speedup /w GC"
):
    """Box plot of commit-author interaction commit node degrees."""

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDESpeedupTargetScatter]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        # print("Dataset: ", data.to_string())

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.5,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax


class PhasarIterIDEMemSpeedupGCPlotBase(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-gc-plot-base',
    yname="Memory Speedup /w GC"
):

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            gc_aggregates = self._get_gc_aggregates(report, ana)

            for jf in [self.JF1, self.JF2]:
                speedups = [float('nan')
                           ] if aggregates[jf] is None or gc_aggregates[
                               jf] is None else speedup_computer(
                                   aggregates[jf].max_resident_sizes,
                                   gc_aggregates[jf].max_resident_sizes
                               )

                for s in speedups:
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            from_kibytes_to_mibytes(
                                np.mean(aggregates[jf].max_resident_sizes)
                            ),
                        "New":
                            from_kibytes_to_mibytes(
                                np.mean(gc_aggregates[jf].max_resident_sizes)
                            ),
                    })

        return nodes


class PhasarIterIDEMemSpeedupGCPlot(
    PhasarIterIDEMemSpeedupGCPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-gc',
    yname="Memory Speedup /w GC"
):
    """Box plot of commit-author interaction commit node degrees."""

    def analysis_order(self) -> tp.List[str]:
        return ["LCA", "Taint", "Typestate"]


class PhasarIterIDEMemSpeedupGCScatterPlot(
    PhasarIterIDEMemSpeedupGCPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-scatter-gc',
    yname="Runtime Speedup /w GC"
):
    """Box plot of commit-author interaction commit node degrees."""

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.5,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Relative Memory Savings")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )

        return ax


# class PhasarIterIDEMemSavingsGCPlot(
#     PhasarIterIDEPlotBase,
#     plot_name='phasar-iter-ide-mem-savings-gc',
#     yname="Memory Savings /w GC [%]"
# ):
#     """Box plot of commit-author interaction commit node degrees."""

#     def _get_data_entries(
#         self, report: PhasarIterIDEStatsReport, cs: str,
#         speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
#     ) -> tp.List[tp.Dict[str, tp.Any]]:
#         nodes: tp.List[tp.Dict[str, tp.Any]] = []

#         for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
#             aggregates = self._get_aggregates(report, ana)
#             gc_aggregates = self._get_gc_aggregates(report, ana)

#             for jf in [self.JF1, self.JF2]:
#                 if aggregates[jf] is None or gc_aggregates[jf] is None:
#                     nodes.append({
#                         self.YNAME: float('nan'),
#                         "JF": self._get_jf_name(jf),
#                         "Analysis": ana,
#                     })
#                     continue
#                 for s in speedup_computer(
#                     aggregates[jf].max_resident_sizes,
#                     gc_aggregates[jf].max_resident_sizes
#                 ):
#                     nodes.append({
#                         self.YNAME: (1 - 1 / s) * 100,
#                         "JF": self._get_jf_name(jf),
#                         "Analysis": ana,
#                     })

#         return nodes

#     def make_phasar_plot(self) -> matplotlib.axes.Axes:
#         ax = self.make_phasar_violinplot()
#         ax.axhline(0)
#         return ax


class PhasarIterIDESpeedupHeatmap(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-speedup-heatmap',
    yname="Best Runtime Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                continue

            Old = aggregates[self.OLD].measurements_wall_clock_time
            JFMeanSpeedups = [
                np.mean(
                    speedup_computer(
                        Old, aggregates[jf].measurements_wall_clock_time
                    )
                ) for jf in range(0, 4) if aggregates[jf] is not None
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
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
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
        # print(f"Runtime Data: {data}")

        return self.heatmap(data, annot)


class PhasarIterIDEMemSpeedupHeatmap(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-mem-speedup-heatmap',
    yname="Best Memory Speedup vs Old"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                continue
            Old = aggregates[self.OLD].max_resident_sizes
            JFMeanSpeedups = [
                np.mean(
                    speedup_computer(Old, aggregates[jf].max_resident_sizes)
                ) for jf in range(0, 4) if aggregates[jf] is not None
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
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
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
        # print(f"Memory Data: {data}")

        return self.heatmap(data, annot)


class PhasarIterIDENewTime(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-new-time',
    yname="Runtime [s]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested]:
                if aggregates[jf] is None:
                    continue
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        self.YNAME: time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
        ax = sns.boxplot(
            x="Analysis",
            y=self.YNAME,
            data=data,
            hue="JF",
            showfliers=False,
        )
        ax.set_ylim(top=600)
        return ax


class PhasarIterIDENewMem(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-new-mem',
    yname="Memory [MB]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested]:
                if aggregates[jf] is None:
                    continue
                for mem in aggregates[jf].max_resident_sizes:
                    nodes.append({
                        self.YNAME: mem / 1000,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
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

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested, self.OLD]:
                if aggregates[jf] is None:
                    continue
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
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
        return self.broken_boxplot(
            data, [1, 2], [15000, 0, 2500], [100000, 55000, 10000]
        )


class PhasarIterIDEOldNewTimeViolinPlot(
    PhasarIterIDEPlotBase,
    plot_name='phasar-iter-ide-old-new-time',
    yname="Runtime [s]"
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF1, self.JF2, self.JF3, self.Nested, self.OLD]:
                if aggregates[jf] is None:
                    continue
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        self.YNAME: time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_speedups)
        return self.broken_boxplot(
            data, [1, 2], [500, 0, 60], [4000, 2250, 500]
        )

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class PhasarIterIDEWLSpeedupScatterPlot(
    Plot, plot_name='phasar-iter-ide-speedup-target-scatter'
):

    YNAME = "Runtime with WorkLists"

    TAINT = "Taint"
    TYPESTATE = "Typestate"
    LCA = "LCA"
    IIA = "IIA"

    JF1 = 0
    JF2 = 1
    JF3 = 2
    OLD = 3

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
        elif ana == self.IIA:
            return [
                report.new_iia_jf1, report.new_iia, report.new_iia_jf3,
                report.old_iia
            ]
        else:
            raise "ERROR: Invalid analysis: " + ana

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

    @staticmethod
    def compute_mean_speedup(
        old_measurements: tp.List[float], new_measurements: tp.List[float]
    ) -> tp.List[float]:
        return [
            np.mean(
                list(
                    map(
                        lambda x: round(x[0] / x[1], 3),
                        itertools.product(old_measurements, new_measurements)
                    )
                )
            )
        ]

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport, cs: str,
        speedup_computer: tp.Callable[[tp.List[float], tp.List[float]], float]
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA, self.IIA]:
            # print(f"Processing {ana} analysis results")
            aggregates = self._get_aggregates(report, ana)
            if aggregates[self.OLD] is None:
                print(f"Skip {ana}")
                continue
            for jf in [self.JF1, self.JF2, self.JF3]:
                if aggregates[jf] is None:
                    print(f"Skip {self._get_jf_name(jf)} for {ana}")
                    continue
                for s in speedup_computer(
                    aggregates[self.OLD].measurements_wall_clock_time,
                    aggregates[jf].measurements_wall_clock_time
                ):
                    # print(f"> {s}")
                    nodes.append({
                        self.YNAME:
                            s,
                        "JF":
                            self._get_jf_name(jf),
                        "Analysis":
                            ana,
                        "Old":
                            np.mean(
                                aggregates[self.OLD
                                          ].measurements_wall_clock_time
                            ),
                        "New":
                            np.mean(
                                aggregates[jf].measurements_wall_clock_time
                            ),
                        "Target":
                            cs,
                    })

        return nodes

    def _get_jf_name(self, jf: int) -> str:
        if jf == self.JF1:
            return "JF1"
        elif jf == self.JF2:
            return "JF4"
        elif jf == self.JF3:
            return "JF4S"
        elif jf == self.OLD:
            return "Old"
        else:
            raise "ERROR: Table Rep out-of-range: " + str(jf)

    def make_dataframe(
        self, speedup_computer: tp.Callable[[tp.List[float], tp.List[float]],
                                            float]
    ) -> pd.DataFrame:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        # print("WL Make Dataframe: ")

        timeouts = dict()
        ooms = dict()
        for case_study in case_studies:
            report_files = get_processed_revisions_files(
                case_study.project_name, IDELinearConstantAnalysisExperimentWL,
                PhasarIterIDEStatsReport,
                get_case_study_file_name_filter(case_study)
            )

            assert len(
                report_files
            ) <= 1, f"Invalid length of report_files list: got {len(report_files)}, expected 1"

            if (len(report_files) == 0):
                print("No report files for ", case_study.project_name)
                continue

            print("Num Reports: ", len(report_files))

            for report_file in report_files:
                # print("Report: ", report_file)
                report = load_phasar_iter_ide_stats_report(report_file)

                local_timeouts = report.aggregate_timeouts()
                merge_dict(timeouts, local_timeouts, lambda x, y: x + y)

                local_ooms = report.aggregate_ooms()
                merge_dict(ooms, local_ooms, lambda x, y: x + y)

                nodes.extend(
                    self._get_data_entries(
                        report, case_study.project_name, speedup_computer
                    )
                )

        print("Timeouts: ", timeouts)
        print("OOMs: ", ooms)
        df = pd.DataFrame(nodes)
        print("WL DataFrame: ", df)
        return df.sort_values(by=["Analysis", "JF"])

    def make_phasar_plot(self) -> matplotlib.axes.Axes:
        data = self.make_dataframe(PhasarIterIDEPlotBase.compute_mean_speedup)

        # for ana in ["Taint", "LCA", "IIA"]:
        #     Rows = data.loc[data["Analysis"] == ana][self.YNAME]
        #     Min = Rows.min()
        #     Max = Rows.max()
        #     Mean = Rows.mean()
        #     print(f"[PhasarIterIDESpeedupTargetScatter]: {ana}: Min {Min}, Max {Max}, Mean {Mean}")

        # print("Dataset: ", data.to_string())

        ax = sns.scatterplot(
            data=data,
            x="Target",
            y=self.YNAME,
            hue="JF",
            style="Analysis",
            linewidth=0,
            alpha=0.7,
        )

        ax.axhline(1, linewidth=1, color='gray')

        ax.set_ylabel("Runtime Speedup")
        ax.set_xlabel("Target Program")
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, horizontalalignment='right'
        )
        # ax.set_xticklabels(ax.get_xticklabels(), rotation=90)

        return ax

    def plot(self, view_mode: bool) -> None:
        ax = self.make_phasar_plot()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def get_argmaxmin(self, Args: tp.List[float]) -> tp.Tuple[int, int]:
        Max = np.argmax(Args)
        Min = np.argmin(Args)
        return (Max, Min)


##
################################################################################
##


class CAIGViolinPlotGenerator(
    PlotGenerator, generator_name="phasar-iter-ide-jf1-jf2", options=[]
):
    """Generates a violin plot showing the distribution of interacting authors
    for each case study."""

    def generate(self) -> tp.List[Plot]:
        return [
            # PhasarIterIDEJF1JF2TimeViolinPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),

            # PhasarIterIDESpeedupScatterPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDEMemSpeedupScatterPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDEOldNewTimeViolinPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDEOldNewMemViolinPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDESpeedupVsJF1Plot(self.plot_config, **self.plot_kwargs),
            # PhasarIterIDEMemSpeedupVsJF1Plot(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDENewTime(self.plot_config, **self.plot_kwargs),
            # PhasarIterIDENewMem(self.plot_config, **self.plot_kwargs),
            # PhasarIterIDESpeedupHeatmap(self.plot_config, **self.plot_kwargs),
            # PhasarIterIDEMemSpeedupHeatmap(
            #     self.plot_config, **self.plot_kwargs
            # ),
            # PhasarIterIDESpeedupGCPlot(self.plot_config, **self.plot_kwargs),
            # PhasarIterIDEMemSpeedupGCPlot(self.plot_config, **self.plot_kwargs),
            PhasarIterIDESpeedupGCScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemSpeedupGCScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEOldNewNestedScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemOldNewNestedScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDESpeedupJFvsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemSpeedupJFvsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEAbsoluteMemSpeedupJFvsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEAbsoluteSpeedupJFvsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetSpeedupVsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetMemSpeedupVsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDECombinedSpeedupPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDELineTargetSpeedupVsNested(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetSpeedupVsNestedSortedSize(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetMemSpeedupVsNestedSortedSize(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetSpeedupVsNestedSortedTime(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDETargetMemSpeedupVsNestedSortedMem(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemGrid(self.plot_config, **self.plot_kwargs),
            PhasarIterIDEGrid(self.plot_config, **self.plot_kwargs),
        ]


class CAIGScatterPlotGenerator(
    PlotGenerator, generator_name="phasar-iter-ide-scatter", options=[]
):
    """Generates a violin plot showing the distribution of interacting authors
    for each case study."""

    def generate(self) -> tp.List[Plot]:
        return [
            PhasarIterIDESpeedupScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDESpeedupTargetScatter(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemSpeedupScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDEMemSpeedupTargetScatter(
                self.plot_config, **self.plot_kwargs
            ),
            PhasarIterIDESpeedupGCScatterPlot(
                self.plot_config, **self.plot_kwargs
            ),
            # PhasarIterIDEWLSpeedupScatterPlot(
            #     self.plot_config, **self.plot_kwargs
            # ),
        ]

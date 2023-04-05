"""Module for BlameInteractionGraph plots."""

import typing as tp
from math import ceil, floor

import networkx as nx
import pandas as pd
import seaborn as sns
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
    TAINT = "Taint"
    TYPESTATE = "Typestate"
    LCA = "LCA"

    JF2 = 0
    JF1 = 1
    JF3 = 2
    OLD = 3

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


class PhasarIterIDEJF1JF2TimeViolinPlot(
    PhasarIterIDEPlotBase, plot_name='phasar-iter-ide-jf1-jf2-time'
):
    """Box plot of commit-author interaction commit node degrees."""

    def _get_data_entries(
        self, report: PhasarIterIDEStatsReport
    ) -> tp.List[tp.Dict[str, tp.Any]]:
        nodes: tp.List[tp.Dict[str, tp.Any]] = []

        for ana in [self.TAINT, self.TYPESTATE, self.LCA]:
            aggregates = self._get_aggregates(report, ana)
            for jf in [self.JF2, self.JF3]:
                for time, old_time in zip(
                    aggregates[jf].measurements_wall_clock_time,
                    aggregates[self.JF1].measurements_wall_clock_time
                ):
                    nodes.append({
                        "Time": (old_time - time) / old_time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def plot(self, view_mode: bool) -> None:
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

        data = pd.DataFrame(nodes).sort_values(by=["Analysis", "JF"])
        ax = sns.violinplot(
            x="Analysis",
            y="Time",
            data=data,
            hue="JF"
            # inner=None,
            # linewidth=1,
            # color=".95"
        )

        # ax.set_ylim(-0.1, 1.1)
        # ax.set_aspect(0.3 / ax.get_data_ratio())
        # ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        # ax.tick_params(axis='y', labelsize=8)
        # ax.set_xlabel(None)
        # ax.yaxis.label.set_size(9)
        # ax.get_legend().remove()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


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
            for jf in [0, 1, 3]:
                for time in aggregates[jf].measurements_wall_clock_time:
                    nodes.append({
                        "Time": time,
                        "JF": self._get_jf_name(jf),
                        "Analysis": ana,
                    })

        return nodes

    def plot(self, view_mode: bool) -> None:
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

        data = pd.DataFrame(nodes).sort_values(by=["Analysis", "JF"])
        ax = sns.boxplot(
            x="Analysis",
            y="Time",
            data=data,
            hue="JF"
            # inner=None,
            # linewidth=1,
            # color=".95"
        )
        ax.set_yscale('log')

        # ax.set_ylim(-0.1, 1.1)
        # ax.set_aspect(0.3 / ax.get_data_ratio())
        # ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        # ax.tick_params(axis='y', labelsize=8)
        # ax.set_xlabel(None)
        # ax.yaxis.label.set_size(9)
        # ax.get_legend().remove()

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
            )
        ]

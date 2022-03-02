"""Module for BlameInteractionGraph plots."""

import logging
import math
import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from varats.data.reports.incremental_reports import IncrementalReport
from varats.jupyterhelper.file import load_incremental_report
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import FullCommitHash

LOG = logging.Logger(__name__)


def _round_delta(base_line: float, increment: float) -> float:
    delta = increment - float(base_line)
    per_delta = delta / float(base_line) * 100
    per_delta = round(per_delta, 2)
    return per_delta


class PhasarIncRevisionDeltaViolinPlot(Plot, plot_name='psr_inc_rev_deltas'):
    """Violing plot to visualize incremental speed deltas for all revisions."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        rev_deltas: tp.List[tp.Dict[str, tp.Any]] = []
        project_names: tp.Set[str] = set()
        for case_study in case_studies:
            project_name = case_study.project_name
            print(f"Processing: {project_name=}")

            report_files = get_processed_revisions_files(
                case_study.project_name, IncrementalReport,
                get_case_study_file_name_filter(case_study)
            )

            if not report_files:
                continue

            for report_file in report_files:
                report = load_incremental_report(report_file)

                rev_delta_lca = _round_delta(
                    report.ide_lca_timings().total_wpa(),
                    report.ide_lca_timings().total_incremental()
                )
                rev_delta_taint = _round_delta(
                    report.ifds_taint_timings().total_wpa(),
                    report.ifds_taint_timings().total_incremental()
                )
                rev_delta_typestate = _round_delta(
                    report.ide_typestate_timings().total_wpa(),
                    report.ide_typestate_timings().total_incremental()
                )

                if math.isnan(rev_delta_lca):
                    continue

                rev_deltas.append({
                    "Project": project_name,
                    "TimeDeltaLCA": rev_delta_lca,
                    "TimeDeltaTaint": rev_delta_taint,
                    "TimeDeltaTypestate": rev_delta_typestate
                })

                project_names.add(project_name)

        if not rev_deltas:
            LOG.warning("There were no projects found with enough data points.")
            raise PlotDataEmpty

        data = pd.DataFrame(rev_deltas)
        print(f"{data=}")

        fig, axes = plt.subplots(3, 1, sharex=True, sharey=True)
        fig.subplots_adjust(hspace=0.03)
        box_style = dict(boxstyle='round', facecolor='blue', alpha=0.3)
        box_fontsize = 8

        # Plot -
        sns.violinplot(
            ax=axes[0],
            x="Project",
            y="TimeDeltaLCA",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            ax=axes[0],
            x="Project",
            y="TimeDeltaLCA",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        axes[0].text(
            0.95,
            0.9,
            "LCA",
            transform=axes[0].transAxes,
            fontsize=box_fontsize,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=box_style
        )

        # Plot -
        sns.violinplot(
            ax=axes[1],
            x="Project",
            y="TimeDeltaTaint",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            ax=axes[1],
            x="Project",
            y="TimeDeltaTaint",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        box_style['facecolor'] = 'green'
        axes[1].text(
            0.95,
            0.9,
            "Taint",
            transform=axes[1].transAxes,
            fontsize=box_fontsize,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=box_style
        )

        # Plot -
        sns.violinplot(
            ax=axes[2],
            x="Project",
            y="TimeDeltaTypestate",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            ax=axes[2],
            x="Project",
            y="TimeDeltaTypestate",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        box_style['facecolor'] = 'red'
        axes[2].text(
            0.95,
            0.9,
            "Typestate",
            transform=axes[2].transAxes,
            fontsize=box_fontsize,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=box_style
        )

        for ax in axes:
            # ax.set_ylim(-0.1, 1.1)
            ax.set_aspect(0.3 / ax.get_data_ratio())
            ax.tick_params(axis='x', labelrotation=45)
            ax.set_xlabel(None)
            ax.set_ylabel(None)

        axes[1].set_ylabel("Analysis Time Reduction in %")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class PIRDViolinPlotGenerator(
    PlotGenerator, generator_name="psr-inc-rev-deltas", options=[]
):
    """Generates a violin plot showing the distribution of incremental analysis
    speedup deltas for each case study."""

    def generate(self) -> tp.List[Plot]:
        return [
            PhasarIncRevisionDeltaViolinPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class PhasarIncHelperAnalysisViolinPlot(
    Plot, plot_name='psr_inc_helper_shares'
):
    """Violing plot to visualize incremental speed deltas for helper
    analyses."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        rev_deltas: tp.List[tp.Dict[str, tp.Any]] = []
        project_names: tp.Set[str] = set()
        for case_study in case_studies:
            project_name = case_study.project_name
            print(f"Processing: {project_name=}")

            report_files = get_processed_revisions_files(
                case_study.project_name, IncrementalReport,
                get_case_study_file_name_filter(case_study)
            )

            if not report_files:
                continue

            for report_file in report_files:
                report = load_incremental_report(report_file)

                def build_data_for_timings(timings, analysis):
                    irdb = timings.inc_incremental_irdb_construction_time
                    irdb_delta = _round_delta(
                        timings.inc_initial_irdb_construction_time,
                        timings.inc_incremental_irdb_construction_time
                    )

                    th = timings.inc_incremental_th_construction_time
                    th_delta = _round_delta(
                        timings.inc_initial_th_construction_time,
                        timings.inc_incremental_th_construction_time
                    )

                    pt = timings.inc_incremental_pt_construction_time
                    pt_delta = _round_delta(
                        timings.inc_initial_pt_construction_time,
                        timings.inc_incremental_pt_construction_time
                    )

                    icfg = timings.inc_incremental_icfg_construction_time
                    icfg_delta = _round_delta(
                        timings.inc_initial_icfg_construction_time,
                        timings.inc_incremental_icfg_construction_time
                    )

                    dfa = timings.inc_incremental_dfa_solving_time
                    dfa_delta = _round_delta(
                        timings.inc_initial_dfa_solving_time,
                        timings.inc_incremental_dfa_solving_time
                    )

                    total = irdb + th + pt + icfg + dfa

                    rev_deltas.append({
                        "Project": project_name,
                        "Analysis": analysis,
                        "AnalysisPart": "IRDB",
                        "Proportion": irdb / total,
                        "Delta": irdb_delta
                    })
                    rev_deltas.append({
                        "Project": project_name,
                        "Analysis": analysis,
                        "AnalysisPart": "TH",
                        "Proportion": th / total,
                        "Delta": th_delta
                    })
                    rev_deltas.append({
                        "Project": project_name,
                        "Analysis": analysis,
                        "AnalysisPart": "PT",
                        "Proportion": pt / total,
                        "Delta": pt_delta
                    })
                    rev_deltas.append({
                        "Project": project_name,
                        "Analysis": analysis,
                        "AnalysisPart": "ICFG",
                        "Proportion": icfg / total,
                        "Delta": icfg_delta
                    })
                    rev_deltas.append({
                        "Project": project_name,
                        "Analysis": analysis,
                        "AnalysisPart": "DFA",
                        "Proportion": dfa / total,
                        "Delta": dfa_delta
                    })

                build_data_for_timings(report.ide_lca_timings(), "lca")
                build_data_for_timings(
                    report.ide_typestate_timings(), "typestate"
                )
                build_data_for_timings(report.ifds_taint_timings(), "taint")

        if not rev_deltas:
            LOG.warning("There were no projects found with enough data points.")
            raise PlotDataEmpty

        helper_analyses = ["IRDB", "TH", "PT", "ICFG", "DFA"]

        data = pd.DataFrame(rev_deltas)
        # pd.set_option("display.max_rows", None, "display.max_columns", None)
        print(f"{data=}")
        ax = sns.violinplot(
            x="AnalysisPart",
            # y="Proportion",
            y="Delta",
            data=data,
            order=helper_analyses,
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="AnalysisPart",
            # y="Proportion",
            y="Delta",
            data=data,
            order=helper_analyses,
            alpha=.25,
            size=3
        )
        # ax.set_ylim(-0.05, None)
        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_xlabel(None)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class PIHAViolinPlotGenerator(
    PlotGenerator, generator_name="psr-inc-helper-shares", options=[]
):
    """Generates a violin plot showing the distribution of incremental analysis
    speedup deltas for each helper analysis."""

    def generate(self) -> tp.List[Plot]:
        return [
            PhasarIncHelperAnalysisViolinPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]

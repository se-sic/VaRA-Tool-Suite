"""Module for BlameInteractionGraph plots."""

import logging
import math
import typing as tp

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

                rev_delta = _round_delta(
                    report.ide_lca_timings().total_wpa(),
                    report.ide_lca_timings().total_incremental()
                )

                if math.isnan(rev_delta):
                    continue

                rev_deltas.append({
                    "Project": project_name,
                    "Analysis Time Reduction": rev_delta
                })

                project_names.add(project_name)

        if not rev_deltas:
            LOG.warning("There were no projects found with enough data points.")
            raise PlotDataEmpty

        data = pd.DataFrame(rev_deltas)
        # print(f"{data=}")
        ax = sns.violinplot(
            x="Project",
            y="Analysis Time Reduction",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="Project",
            y="Analysis Time Reduction",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        # ax.set_ylim(-0.1, 1.1)
        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_xlabel(None)

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


class PhasarIncHelperAnalysisViolinPlot(Plot, plot_name='psr_inc_rev_deltas'):
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

                rev_delta = _round_delta(
                    report.ide_lca_timings().total_wpa(),
                    report.ide_lca_timings().total_incremental()
                )

                if math.isnan(rev_delta):
                    continue

                rev_deltas.append({
                    "Project": project_name,
                    "Analysis Time Reduction": rev_delta
                })

                irdb = report.ide_lca_timings(
                ).inc_incremental_irdb_construction_time
                th = report.ide_lca_timings(
                ).inc_incremental_th_construction_time
                pt = report.ide_lca_timings(
                ).inc_incremental_pt_construction_time
                icfg = report.ide_lca_timings(
                ).inc_incremental_icfg_construction_time
                dfa = report.ide_lca_timings().inc_incremental_dfa_solving_time

                total = irdb + th + pt + icfg + dfa

                rev_deltas.append({
                    "Project": project_name,
                    "Analysis": "IRDB",
                    "Proportion": irdb / total
                })
                rev_deltas.append({
                    "Project": project_name,
                    "Analysis": "TH",
                    "Proportion": th / total
                })
                rev_deltas.append({
                    "Project": project_name,
                    "Analysis": "PT",
                    "Proportion": pt / total
                })
                rev_deltas.append({
                    "Project": project_name,
                    "Analysis": "ICFG",
                    "Proportion": icfg / total
                })
                rev_deltas.append({
                    "Project": project_name,
                    "Analysis": "DFA",
                    "Proportion": dfa / total
                })

                # rev_deltas.append(time_data)

                # project_names.add(project_name)

        if not rev_deltas:
            LOG.warning("There were no projects found with enough data points.")
            raise PlotDataEmpty

        project_names = {"IRDB", "TH", "PT", "ICFG", "DFA"}

        data = pd.DataFrame(rev_deltas)
        print(f"{data=}")
        ax = sns.violinplot(
            x="Analysis",
            y="Proportion",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="Analysis",
            y="Proportion",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        ax.set_ylim(-0.05, None)
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

"""Module for blame report time metrics."""
import logging
import typing as tp

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot
from varats.plot.plot_utils import annotate_correlation
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilename
from varats.report.wall_time_report import WallTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import num_project_commits, FullCommitHash

LOG = logging.Logger(__name__)


class BlameTimeMetricsPlot(Plot, plot_name="blame_time_metrics_plot"):
    """Plot showing correlation between blame annotation time and history
    size."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReportExperiment, WallTimeReportAggregate
            )
            if revision is None:
                continue

            def match_revision(file_name: str) -> bool:
                return ReportFilename(
                    file_name
                ).commit_hash != revision.to_short_commit_hash()

            gb_agg_reports = get_processed_revisions_files(
                project_name,
                BlameReportExperiment,
                WallTimeReportAggregate,
                file_name_filter=match_revision
            )
            if not gb_agg_reports:
                continue

            report_agg = WallTimeReportAggregate(gb_agg_reports[0].full_path())
            times = pd.Series([
                report.wall_time.total_seconds()
                for report in report_agg.reports()
            ])

            commits = num_project_commits(project_name, revision)

            cs_dict = pd.DataFrame.from_dict({
                project_name: {
                    "Commits": commits,
                    "Blame Time": times.mean()
                }
            },
                                             orient="index")

            cs_data.append(cs_dict)

        df = pd.concat(cs_data).sort_index()

        grid = sns.lmplot(
            df,
            x="Commits",
            y="Blame Time",
            ci=0,
            robust=True,
            scatter_kws={
                "s": 200,
                "alpha": 0.5
            },
            line_kws={
                "color": "#777777",
                "linewidth": 4
            }
        )
        ax = grid.ax
        annotate_correlation(
            x_values=df["Commits"], y_values=df["Blame Time"], ax=ax
        )
        ax.set_xlabel(None)
        ax.set_ylabel(None)
        ax.tick_params(labelsize=15)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CaseStudyMetricsPLotGenerator(
    PlotGenerator, generator_name="blame-time-correlation", options=[]
):
    """Generates a table showing time metrics for the blame report
    experiment."""

    def generate(self) -> tp.List[Plot]:
        return [BlameTimeMetricsPlot(self.plot_config, **self.plot_kwargs)]

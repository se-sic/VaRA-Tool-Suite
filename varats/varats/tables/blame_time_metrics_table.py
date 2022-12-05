"""Module for blame report time metrics."""
import logging
import typing as tp

import pandas as pd
from scipy.stats import pearsonr, spearmanr

from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.report.report import ReportFilename
from varats.report.wall_time_report import WallTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_project_loc, num_project_commits

LOG = logging.Logger(__name__)


class BlameTimeMetricsTable(Table, table_name="blame_time_metrics_table"):
    """Table showing timing information about the blame report experiment."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReportExperiment
            )
            if revision is None:
                continue

            def match_revision(file_name: str) -> bool:
                return ReportFilename(
                    file_name
                ).commit_hash != revision.to_short_commit_hash()

            blame_reports = get_processed_revisions_files(
                project_name,
                BlameReportExperiment,
                file_name_filter=match_revision
            )
            gb_agg_reports = get_processed_revisions_files(
                project_name,
                BlameReportExperiment,
                WallTimeReportAggregate,
                file_name_filter=match_revision
            )
            if not blame_reports or not gb_agg_reports:
                continue

            blame_report = load_blame_report(blame_reports[0].full_path())
            report_agg = WallTimeReportAggregate(gb_agg_reports[0].full_path())
            times = pd.Series([
                report.wall_time.total_seconds()
                for report in report_agg.reports()
            ])

            commits = num_project_commits(project_name, revision)
            loc = calc_project_loc(project_name, revision)

            cs_dict = pd.DataFrame.from_dict({
                project_name: {
                    "LOC":
                        loc,
                    "Commits":
                        commits,
                    "Blame Time":
                        times.mean(),
                    "Blame Time/Commit":
                        times.sum() / commits,
                    "Blame Time/LOC":
                        times.sum() / loc,
                    "Analysis Time":
                        blame_report.meta_data.bta_wall_time,
                    "Analysis Time/LOC":
                        (blame_report.meta_data.bta_wall_time or 0) / loc
                }
            },
                                             orient="index")

            cs_data.append(cs_dict)

        df = pd.concat(cs_data).sort_index()
        blame_vs_commits_p, _ = pearsonr(df["Blame Time"], df["Commits"])
        blame_vs_commits_s, _ = spearmanr(df["Blame Time"], df["Commits"])
        blame_vs_loc_p, _ = pearsonr(df["Blame Time"], df["LOC"])
        blame_vs_loc_s, _ = spearmanr(df["Blame Time"], df["LOC"])
        analysis_vs_loc_p, _ = pearsonr(df["Analysis Time"], df["LOC"])
        analysis_vs_loc_s, _ = spearmanr(df["Analysis Time"], df["LOC"])

        df = pd.concat([
            df,
            pd.DataFrame.from_dict({
                r"$\rho_{pearson}$": {
                    "Commits": None,
                    "LOC": None,
                    "Blame Time": None,
                    "Blame Time/Commit": blame_vs_commits_p,
                    "Blame Time/LOC": blame_vs_loc_p,
                    "Analysis Time": None,
                    "Analysis Time/LOC": analysis_vs_loc_p
                }
            },
                                   orient="index"),
            pd.DataFrame.from_dict({
                r"$\rho_{spearman}$": {
                    "Commits": None,
                    "LOC": None,
                    "Blame Time": None,
                    "Blame Time/Commit": blame_vs_commits_s,
                    "Blame Time/LOC": blame_vs_loc_s,
                    "Analysis Time": None,
                    "Analysis Time/LOC": analysis_vs_loc_s
                }
            },
                                   orient="index")
        ])

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            df.rename(
                columns={
                    "Commits":
                        "Commits",
                    "LOC":
                        "LOC",
                    "Blame Time":
                        r"$t_{\text{Blame}}$",
                    "Blame Time/Commit":
                        r"$\frac{t_{\text{Blame}}}{\text{Commit}}$",
                    "Blame Time/LOC":
                        r"$\frac{t_{\text{Blame}}}{\text{LOC}}$",
                    "Analysis Time":
                        r"$t_{\text{Analysis}}$",
                    "Analysis Time/LOC":
                        r"$\frac{t_{\text{Analysis}}}{\text{LOC}}$",
                },
                inplace=True
            )
            kwargs["hrules"] = True
            kwargs["caption"] = \
                f"Blame Time vs. Commits: " \
                f"$\\mathit{{\\rho_p}} = {blame_vs_commits_p:.2f}$, " \
                f"$\\mathit{{\\rho_s}} = {blame_vs_commits_s:.2f}$\n" \
                f"Blame Time vs. LOC: " \
                f"$\\mathit{{\\rho_p}} = {blame_vs_loc_p:.2f}$, " \
                f"$\\mathit{{\\rho_s}} = {blame_vs_loc_s:.2f}$\n" \
                f"Analysis Time vs. Commits: " \
                f"$\\mathit{{\\rho_p}} = {analysis_vs_loc_p:.2f}$, " \
                f"$\\mathit{{\\rho_s}} = {analysis_vs_loc_s:.2f}$\n"

            style = df.style
            style = style.format(
                subset=[
                    r"$t_{\text{Blame}}$",
                    r"$\frac{t_{\text{Blame}}}{\text{Commit}}$",
                    r"$\frac{t_{\text{Blame}}}{\text{LOC}}$",
                    r"$t_{\text{Analysis}}$",
                    r"$\frac{t_{\text{Analysis}}}{\text{LOC}}$"
                ],
                precision=2,
                thousands=r"\,",
                na_rep=""
            ).format(
                subset=["Commits", "LOC"],
                precision=0,
                thousands=r"\,",
                na_rep=""
            )

        return dataframe_to_table(df, table_format, style, wrap_table, **kwargs)


class CaseStudyMetricsTableGenerator(
    TableGenerator, generator_name="blame-time-metrics-table", options=[]
):
    """Generates a table showing time metrics for the blame report
    experiment."""

    def generate(self) -> tp.List[Table]:
        return [BlameTimeMetricsTable(self.table_config, **self.table_kwargs)]

"""Module for blame report time metrics."""
import logging
import typing as tp

import pandas as pd

from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.project.project_util import (
    get_local_project_git_path,
    get_local_project_git,
)
from varats.report.wall_time_report import WallTimeReportAggregate
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import num_commits, calc_repo_loc

LOG = logging.Logger(__name__)


class BlameTimeMetricsTable(Table, table_name="blame_time_metrics_table"):
    """Table showing timing information about the blame report experiment."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            project_repo = get_local_project_git(project_name)
            project_git_path = get_local_project_git_path(project_name)
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReportExperiment
            )
            if not revision:
                continue

            blame_reports = get_processed_revisions_files(
                project_name, BlameReportExperiment
            )
            gb_agg_reports = get_processed_revisions_files(
                project_name, BlameReportExperiment, WallTimeReportAggregate
            )
            if not blame_reports or not gb_agg_reports:
                continue

            blame_report = load_blame_report(blame_reports[0].full_path())
            report_agg = WallTimeReportAggregate(gb_agg_reports[0].full_path())
            times = pd.Series([
                report.wall_time.total_seconds()
                for report in report_agg.reports()
            ])

            commits = num_commits(revision.hash, project_git_path)
            rev_range = revision.hash if revision else "HEAD"
            loc = calc_repo_loc(project_repo, rev_range)
            cs_dict = pd.DataFrame.from_dict({
                project_name: {
                    "Commits":
                        commits,
                    "Blame Time":
                        times.mean(),
                    "Blame Time/Commit":
                        times.sum() / commits,
                    "Analysis Time":
                        blame_report.meta_data.bta_wall_time,
                    "Analysis Time/LOC":
                        blame_report.meta_data.bta_wall_time / loc
                }
            },
                                             orient="index")

            cs_data.append(cs_dict)

        df = pd.concat(cs_data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            style.format(precision=0)

        return dataframe_to_table(df, table_format, style, wrap_table, **kwargs)


class CaseStudyMetricsTableGenerator(
    TableGenerator, generator_name="blame-time-metrics-table", options=[]
):
    """Generates a table showing time metrics for the blame report
    experiment."""

    def generate(self) -> tp.List[Table]:
        return [BlameTimeMetricsTable(self.table_config, **self.table_kwargs)]

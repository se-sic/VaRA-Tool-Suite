"""Module for code centrality tables."""
import logging
import typing as tp

import pandas as pd
from benchbuild.utils.cmd import git
from tabulate import tabulate

from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat
from varats.utils.git_util import calc_repo_loc

LOG = logging.Logger(__name__)


class CaseStudyMetricsTable(Table):
    """Table showing some general information about the case studies in a paper
    config."""

    NAME = "cs_metrics"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            project_cls = get_project_cls_by_name(project_name)
            project_repo = get_local_project_git(project_name)
            project_path = project_repo.path[:-5]
            project_git = git["-C", project_path]

            revision = self.table_kwargs.get("revisions", {}).get(
                case_study.project_name, None
            )
            revisions = case_study.revisions
            if not revision and len(revisions) == 1:
                revision = revisions[0]
            rev_range = revision.hash if revision else "HEAD"

            cs_dict = {
                project_name: {
                    "Domain":
                        str(project_cls.DOMAIN)[0].upper() +
                        str(project_cls.DOMAIN)[1:],
                    "LOC":
                        calc_repo_loc(project_repo, rev_range),
                    "Commits":
                        int(project_git("rev-list", "--count", rev_range)),
                    "Authors":
                        len(
                            project_git("shortlog", "-s",
                                        rev_range).splitlines()
                        )
                }
            }
            if revision:
                cs_dict[project_name]["Revision"] = revision.short_hash

            cs_data.append(pd.DataFrame.from_dict(cs_dict, orient="index"))

        df = pd.concat(cs_data).sort_index()
        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            table = df.to_latex(
                bold_rows=True, multicolumn_format="c", multirow=True
            )
            return str(table) if table else ""
        return tabulate(df, df.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)

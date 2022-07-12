"""Module for code centrality tables."""
import logging
import typing as tp

import pandas as pd
from benchbuild.utils.cmd import git

from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
)
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc

LOG = logging.Logger(__name__)


class CaseStudyMetricsTable(Table, table_name="cs_metrics_table"):
    """Table showing some general information about the case studies in a paper
    config."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        cs_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            commit_map = get_commit_map(project_name)
            project_cls = get_project_cls_by_name(project_name)
            project_repo = get_local_project_git(project_name)
            project_path = project_repo.path[:-5]
            project_git = git["-C", project_path]

            revisions = sorted(
                case_study.revisions, key=commit_map.time_id, reverse=True
            )
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

        kwargs: tp.Dict[str, tp.Any] = {"bold_rows": True}
        if table_format.is_latex():
            kwargs["multicolumn_format"] = "c"
            kwargs["multirow"] = True

        return dataframe_to_table(
            df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class CaseStudyMetricsTableGenerator(
    TableGenerator, generator_name="cs-metrics-table", options=[]
):
    """Generates a cs-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [CaseStudyMetricsTable(self.table_config, **self.table_kwargs)]

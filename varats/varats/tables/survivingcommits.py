"""Module for code centrality tables."""
import logging
import typing as tp
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from varats.data.databases.blame_interaction_database import (
    BlameInteractionDatabase,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import load_case_study_from_file
from varats.project.project_util import get_local_project_git
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat
from varats.utils.git_util import calc_surviving_lines

LOG = logging.Logger(__name__)


class SurvivingInteractionsTable(Table):

    NAME = "surviving_interactions"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_study = load_case_study_from_file(
            Path(self.table_kwargs['cs_path'])
        )
        project_name = case_study.project_name
        data = BlameInteractionDatabase().get_data_for_project(
            project_name, [
                "IN_HEAD_Interactions", "time_id", "revision",
                'OUT_HEAD_Interactions', 'HEAD_Interactions'
            ], get_commit_map(project_name), case_study
        )
        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            table = data.to_latex(
                bold_rows=True, multicolumn_format="c", multirow=True
            )
            return str(table) if table else ""
        return tabulate(data, data.columns, self.format.value)

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)


class SurvivingLinesTable(Table):
    """Table surviving lines of the commits in a case study sampled at the
    commits of the case study."""

    NAME = "surviving_lines"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        case_study = load_case_study_from_file(
            Path(self.table_kwargs['cs_path'])
        )

        cs_data: tp.List[pd.DataFrame] = []

        project_name = case_study.project_name
        project_repo = get_local_project_git(project_name)
        for revision in case_study.revisions:
            lines_per_revision = calc_surviving_lines(project_repo, revision)
            rev_dict = {
                revision: {
                    k: v
                    for (k, v) in lines_per_revision.items()
                    if case_study.revisions.__contains__(k)
                }
            }
            cs_data.append(pd.DataFrame.from_dict(rev_dict, orient="index"))
        df = pd.concat(cs_data)
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

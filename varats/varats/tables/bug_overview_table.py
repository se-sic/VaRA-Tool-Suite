"""Module for writing bug-data metrics tables."""
import typing as tp

import numpy as np
import pandas as pd

from varats.paper.case_study import CaseStudy
from varats.project.project_util import get_project_cls_by_name
from varats.provider.bug.bug_provider import BugProvider
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY


class BugOverviewTable(Table, table_name="bug_overview_table"):
    """Visualizes bug metrics of a project."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        project_name: str = self.table_kwargs['case_study'].project_name

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )

        variables = [
            "fixing hash", "fixing message", "fixing author", "issue_number"
        ]
        pybugs = bug_provider.find_pygit_bugs()

        data_rows = [[
            pybug.fixing_commit.hex, pybug.fixing_commit.message,
            pybug.fixing_commit.author.name, pybug.issue_id
        ] for pybug in pybugs]

        bug_df = pd.DataFrame(columns=variables, data=np.array(data_rows))

        kwargs: tp.Dict[str, tp.Any] = {"bold_rows": True}
        if table_format.is_latex():
            kwargs["multicolumn_format"] = "c"
            kwargs["longtable"] = True

        return dataframe_to_table(
            bug_df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class BugOverviewTableGenerator(
    TableGenerator,
    generator_name="bug-overview-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a bug-overview table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")

        return [
            BugOverviewTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies
        ]

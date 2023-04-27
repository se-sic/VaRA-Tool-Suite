import typing as tp

import pandas as pd

from varats.paper.case_study import CaseStudy
from varats.plots.commit_trend import lines_per_interactions_squashed
from varats.plots.surviving_commits import lines_and_interactions
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY


class CommitSurvivalTable(Table, table_name="commit_survival"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_and_interactions(case_study)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class CommitSurvivalChangesTable(Table, table_name="interactions_loc_change"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_per_interactions_squashed(case_study)
        data_frame = data_frame.pivot(
            index="revision", columns="base_hash", values="interactions"
        )
        data_frame.sort_index(axis=0, inplace=True)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class CommtiSurvivalGenerator(
    TableGenerator,
    generator_name="commit_survival",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.table.table.Table']:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")
        return [
            CommitSurvivalChangesTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            ),
            CommitSurvivalTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            )
        ]
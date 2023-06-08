import typing as tp

import pandas as pd

from varats.paper.case_study import CaseStudy
from varats.plots.commit_trend import lines_per_interactions_squashed
from varats.plots.interactions_change_distribution import (
    revision_impact,
    impact_data,
)
from varats.plots.surviving_commits import lines_and_interactions
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)


class CommitSurvivalTable(Table, table_name="commit_survival"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]
        data_frame: pd.DataFrame = lines_and_interactions(case_study)
        return dataframe_to_table(
            data_frame, table_format, wrap_table=wrap_table
        )


class Impact(Table, table_name="revision_impact"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studys: tp.List[CaseStudy] = self.table_kwargs["case_study"]
        data = pd.DataFrame({
            "revision": [],
            "interactions": [],
            "interaction_change": [],
            "lines": [],
            "line_change": [],
            "impacted_commits": [],
            "project": [],
        })
        for case_study in case_studys:
            cs_data = revision_impact(case_study)
            cs_data.insert(1, "project", case_study.project_name)
            data = pd.concat([data, cs_data],
                             ignore_index=True,
                             copy=False,
                             join="inner")
        return dataframe_to_table(data, table_format, wrap_table=wrap_table)


class ImpactCorrelation(Table, table_name="impact_correlation"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studys: tp.List[CaseStudy] = self.table_kwargs["case_study"]
        data = impact_data(case_studys)
        return dataframe_to_table(
            data.corr(), table_format, wrap_table=wrap_table
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


class ImpactTableGenerator(
    TableGenerator,
    generator_name="revision-impact",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List['varats.table.table.Table']:
        return [
            Impact(self.table_config, **self.table_kwargs),
            ImpactCorrelation(self.table_config, **self.table_kwargs)
        ]

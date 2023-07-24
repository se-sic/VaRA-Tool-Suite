import typing as tp

import numpy as np
import pandas as pd

from varats.paper.case_study import CaseStudy
from varats.plots.feature_blame_plots import get_dataflow_data_for_case_study
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import num_commits


class DFBREvalTable(Table, table_name="dfbr_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs['case_study']

        data = get_dataflow_data_for_case_study(case_study)

        rows = []

        commits_not_part_of_feature = data.loc[data['part_of_feature'] == 0]

        avg_not_part_of_feature = np.mean(
            commits_not_part_of_feature['num_interacting_features']
        )
        rows.append([
            'avg_num_interacting_features_for_commits_not_part_of_feature',
            avg_not_part_of_feature
        ])

        commits_part_of_feature = data.loc[data['part_of_feature'] == 1]

        avg_part_of_feature = np.mean(
            commits_part_of_feature['num_interacting_features']
        )
        rows.append([
            'avg_num_interacting_features_for_commits_part_of_feature',
            avg_part_of_feature
        ])

        fraction_all_commits = len(
            data.loc[data['num_interacting_features'] > 0]
        ) / (len(data))
        rows.append([
            'fraction_all_commits_interacting_with_features',
            fraction_all_commits
        ])

        fraction_commits_part_of_feature = len(
            commits_part_of_feature.loc[
                commits_part_of_feature['num_interacting_features'] > 0]
        ) / len(commits_part_of_feature)
        rows.append([
            'fraction_commits_part_of_feature_interacting_with_features',
            fraction_commits_part_of_feature
        ])

        fraction_commits_not_part_of_feature = len(
            commits_not_part_of_feature.loc[
                commits_not_part_of_feature['num_interacting_features'] > 0]
        ) / len(commits_not_part_of_feature)
        rows.append([
            'fraction_commits_not_part_of_feature_interacting_with_features',
            fraction_commits_not_part_of_feature
        ])

        df = pd.DataFrame(rows, columns=['meaning', 'value'])

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["caption"] = (
                f"Evaluation of project {case_study.project_name}. "
            )
            kwargs['position'] = 't'

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class DFBREvalTableGenerator(
    TableGenerator,
    generator_name="dfbr-eval-table",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")
        return [
            DFBREvalTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            )
        ]
    

class DFBRInterestingCommitsTable(Table, table_name="dfbr_interesting_commits_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs['case_study']

        data = get_dataflow_data_for_case_study(case_study)

        rows = []
        
        data_points_with_many_interactions = data.loc[data['num_interacting_features'] >= 5]

        df = data_points_with_many_interactions
        df.sort_values(by=['part_of_feature'])

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["caption"] = (
                f"Evaluation of project {case_study.project_name}. "
            )
            kwargs['position'] = 't'

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class DFBRInterestingCommitsTableGenerator(
    TableGenerator,
    generator_name="dfbr-interesting-commits-table",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")
        return [
            DFBRInterestingCommitsTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            )
        ]

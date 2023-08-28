import typing as tp

import numpy as np
import pandas as pd

from varats.paper.case_study import CaseStudy
from varats.plots.feature_blame_plots import (
    get_structural_commit_data_for_case_study,
    get_structural_feature_data_for_case_study,
    get_commit_dataflow_data_for_case_study,
    get_feature_dataflow_data_for_case_study,
)
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)


class SFBREvalTable(Table, table_name="sfbr_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs['case_studies']

        projects_data_commits = [
            get_structural_commit_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        projects_data_features = [
            get_structural_feature_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[
            "Average Number of Features Changed for Commits"
        ], [
            "Average Number of Features Changed for Commits (Outliers Filtered)"
        ], [
            "Fraction Commits Changing More Than One Feature"
        ], [
            "Correlation Between Feature Size and Number of Interacting Commits"
        ]]

        for data_commits, data_features in zip(
            projects_data_commits, projects_data_features
        ):

            data_commits_num_interacting_features = data_commits[
                'num_interacting_features']
            commit_average_number_of_features_changed = np.mean(
                data_commits_num_interacting_features
            )
            rows[0].append(commit_average_number_of_features_changed)

            # filtering outliers (3.5 * variance) times greater number of interacting features than the mean
            data_commits_outliers_filtered = data_commits_num_interacting_features[
                abs(
                    data_commits_num_interacting_features -
                    np.mean(data_commits_num_interacting_features)
                ) < 3.5 * np.std(data_commits_num_interacting_features)]
            commit_average_number_of_features_changed_outliers_filtered = np.mean(
                data_commits_outliers_filtered
            )
            rows[1].append(
                commit_average_number_of_features_changed_outliers_filtered
            )

            fraction_commits_changing_more_than_one_feature = len(
                data_commits_num_interacting_features.loc[
                    data_commits_num_interacting_features > 1]
            ) / len(data_commits_num_interacting_features)
            rows[2].append(fraction_commits_changing_more_than_one_feature)

            feature_correlation_between_size_num_interacting_commits = np.corrcoef(
                data_features['num_interacting_commits'],
                data_features['feature_size']
            )[0][1]
            rows[3].append(
                feature_correlation_between_size_num_interacting_commits
            )

        # calc overall mean for each row
        for i in range(0, len(rows)):
            rows[i].append(np.mean(rows[i][1:]))

        df = pd.DataFrame(
            rows,
            columns=['Projects'] +
            [case_study.project_name for case_study in case_studies] +
            ['Overall Mean']
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs["caption"] = (
                f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            )
            kwargs['position'] = 't'

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class SFBREvalTableGenerator(
    TableGenerator,
    generator_name="sfbr-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            SFBREvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class DFBREvalTable(Table, table_name="dfbr_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs['case_studies']

        projects_data_commits = [
            get_commit_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        projects_data_features = [
            get_feature_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [
            [
                "Average Number of Interacting Features for Commits Not Part of Features"
            ],
            [
                "Average Number of Interacting Features for Commits Part of Features"
            ], ["Fraction of All Commits Interacting With Features"],
            ["Fraction of Commits Part of Features Interacting With Features"],
            [
                "Fraction of Commits Not Part of Features Interacting With Features"
            ],
            [
                "Correlation Feature Size Number of Interacting Commits Not Part of Feature"
            ],
            [
                "Correlation Feature Size Number of Interacting Commits Part of Feature"
            ]
        ]

        for data_commits, data_features in zip(
            projects_data_commits, projects_data_features
        ):

            commits_not_part_of_feature = data_commits.loc[
                data_commits['part_of_feature'] == 0]

            avg_not_part_of_feature = np.mean(
                commits_not_part_of_feature['num_interacting_features']
            )
            rows[0].append(avg_not_part_of_feature)

            commits_part_of_feature = data_commits.loc[
                data_commits['part_of_feature'] == 1]

            avg_part_of_feature = np.mean(
                commits_part_of_feature['num_interacting_features']
            )
            rows[1].append(avg_part_of_feature)

            fraction_all_commits = len(
                data_commits.loc[data_commits['num_interacting_features'] > 0]
            ) / (len(data_commits))
            rows[2].append(fraction_all_commits)

            fraction_commits_part_of_feature = len(
                commits_part_of_feature.loc[
                    commits_part_of_feature['num_interacting_features'] > 0]
            ) / len(commits_part_of_feature)
            rows[3].append(fraction_commits_part_of_feature)

            fraction_commits_not_part_of_feature = len(
                commits_not_part_of_feature.loc[
                    commits_not_part_of_feature['num_interacting_features'] > 0]
            ) / len(commits_not_part_of_feature)
            rows[4].append(fraction_commits_not_part_of_feature)

            corr_feature_size_num_interacting_commits_outside = np.corrcoef(
                data_features["num_interacting_commits_outside"],
                data_features["feature_size"]
            )[0][1]
            rows[5].append(corr_feature_size_num_interacting_commits_outside)

            corr_feature_size_num_interacting_commits_inside = np.corrcoef(
                data_features["num_interacting_commits_inside"],
                data_features["feature_size"]
            )[0][1]
            rows[6].append(corr_feature_size_num_interacting_commits_inside)

        # calc overall mean for each row
        for i in range(0, len(rows)):
            rows[i].append(np.mean(rows[i][1:]))

        df = pd.DataFrame(
            rows,
            columns=["Projects"] +
            [case_study.project_name for case_study in case_studies] +
            ['Overall Mean']
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs["caption"] = (
                f"Evaluation of dataflow-based CFIs for projects {projects_separated_by_comma}. "
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
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            DFBREvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class DFBRInterestingCommitsTable(
    Table, table_name="dfbr_interesting_commits_table"
):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs['case_study']

        data = get_dataflow_data_for_case_study(case_study)

        rows = []

        data_points_with_many_interactions = data.loc[
            data['num_interacting_features'] >= 5]

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

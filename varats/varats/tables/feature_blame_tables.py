import typing as tp

import numpy as np
import pandas as pd
from scipy import stats

from varats.data.metrics import apply_tukeys_fence
from varats.paper.case_study import CaseStudy
from varats.plots.feature_blame_plots import (
    get_structural_commit_data_for_case_study,
    get_structural_feature_data_for_case_study,
    get_commit_specific_dataflow_data_for_case_study,
    get_general_commit_dataflow_data_for_case_study,
    get_feature_dataflow_data_for_case_study,
    get_structural_feature_author_data_for_case_study,
    get_dataflow_feature_author_data_for_case_study,
)
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)


class SFBRFeatureEvalTable(Table, table_name="sfbr_feature_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_features = [
            get_structural_feature_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"], ["Variance"]
        ]

        for data_features, current_row in zip(
            projects_data_features,
            range(0, len(case_studies)),
        ):
            corr_def_feature_size_num_interacting_commits_nd1, p_value = stats.pearsonr(
                data_features["num_interacting_commits_nd1"].values,
                data_features["def_feature_size"].values
            )
            rows[current_row].extend([
                corr_def_feature_size_num_interacting_commits_nd1, p_value
            ])
            corr_pot_feature_size_num_interacting_commits, p_value = stats.pearsonr(
                data_features["num_interacting_commits_nd>1"].values +
                data_features["num_interacting_commits_nd1"].values,
                data_features["pot_feature_size"]
            )
            rows[current_row].extend([
                corr_pot_feature_size_num_interacting_commits, p_value
            ])

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))
        rows.pop()

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Corr Def Ftr Size - Cmmts ND1",
                "P-Value",
                "Corr Pot Ftr Size - Any Cmmts",
                "P-Value",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class SFBRFeatureEvalTableGenerator(
    TableGenerator,
    generator_name="sfbr-feature-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            SFBRFeatureEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class SFBRCommitAvgEvalTable(Table, table_name="sfbr_commit_avg_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_commits = [
            get_structural_commit_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        print(projects_data_commits[0])
        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_commits, current_row in zip(
            projects_data_commits,
            range(0, len(case_studies)),
        ):
            data_commits_num_interacting_features = data_commits[
                "num_interacting_features"]

            commit_average_number_of_features_changed = np.mean([
                sum(data_commits_num_interacting_features[i])
                for i in range(len(data_commits))
            ])
            rows[current_row].append(commit_average_number_of_features_changed)

            commit_average_number_of_features_changed_nd1 = np.mean([
                data_commits_num_interacting_features[i][0]
                for i in range(len(data_commits))
            ])
            rows[current_row].append(
                commit_average_number_of_features_changed_nd1
            )

            # filter large commits
            data_commits_num_interacting_features_outliers_filtered = (
                apply_tukeys_fence(data_commits, "commit_size",
                                   1.5)["num_interacting_features"]
            )
            commit_average_number_of_features_changed_outliers_filtered = np.mean(
                [
                    sum(
                        data_commits_num_interacting_features_outliers_filtered[
                            index]
                    ) for index in
                    data_commits_num_interacting_features_outliers_filtered.
                    index
                ]
            )
            rows[current_row].append(
                commit_average_number_of_features_changed_outliers_filtered
            )

            commit_average_number_of_features_changed_outliers_filtered_nd1 = np.mean(
                [
                    data_commits_num_interacting_features_outliers_filtered[
                        index][0] for index in
                    data_commits_num_interacting_features_outliers_filtered.
                    index
                ]
            )
            rows[current_row].append(
                commit_average_number_of_features_changed_outliers_filtered_nd1
            )

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Avg Num Ftrs Chngd",
                "Only ND1",
                "Lrg Cmmts Fltrd",
                "Only ND1 + Lrg Cmmts Fltrd",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class SFBRCommitAvgEvalTableGenerator(
    TableGenerator,
    generator_name="sfbr-commit-avg-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            SFBRCommitAvgEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]
    

class SFBRCommitFracEvalTable(Table, table_name="sfbr_commit_frac_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_commits = [
            get_structural_commit_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        print(projects_data_commits[0])
        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_commits, current_row in zip(
            projects_data_commits,
            range(0, len(case_studies)),
        ):
            data_commits_num_interacting_features = data_commits["num_interacting_features"]
            # filter large commits
            data_commits_num_interacting_features_outliers_filtered = (
                apply_tukeys_fence(data_commits, "commit_size",
                                   1.5)["num_interacting_features"]
            )

            fraction_commits_changing_more_than_one_feature = sum([
                sum(data_commits_num_interacting_features[index]) > 1
                for index in data_commits_num_interacting_features.index
            ]) / len(data_commits_num_interacting_features)
            rows[current_row].append(
                fraction_commits_changing_more_than_one_feature
            )

            fraction_commits_changing_more_than_one_feature_nd1 = sum([
                data_commits_num_interacting_features[index][0] > 1
                for index in data_commits_num_interacting_features.index
            ]) / len(data_commits_num_interacting_features)
            rows[current_row].append(
                fraction_commits_changing_more_than_one_feature_nd1
            )

            fraction_commits_changing_more_than_one_feature_outliers_filtered = sum(
                [
                    sum(
                        data_commits_num_interacting_features_outliers_filtered[
                            index]
                    ) > 1 for index in
                    data_commits_num_interacting_features_outliers_filtered.
                    index
                ]
            ) / len(data_commits_num_interacting_features_outliers_filtered)
            rows[current_row].append(
                fraction_commits_changing_more_than_one_feature_outliers_filtered
            )

            fraction_commits_changing_more_than_one_feature_outliers_filtered_nd1 = sum(
                [
                    data_commits_num_interacting_features_outliers_filtered[
                        index][0] > 1 for index in
                    data_commits_num_interacting_features_outliers_filtered.
                    index
                ]
            ) / len(data_commits_num_interacting_features_outliers_filtered)
            rows[current_row].append(
                fraction_commits_changing_more_than_one_feature_outliers_filtered_nd1
            )

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Frac Cmmts Interacting with >1 Feature",
                "Only ND1",
                "Lrg Cmmts Fltrd",
                "Only ND1 + Lrg Cmmts Fltrd",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class SFBRCommitFracEvalTableGenerator(
    TableGenerator,
    generator_name="sfbr-commit-frac-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            SFBRCommitFracEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class SFBRAuthorEvalTable(Table, table_name="sfbr_author_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_authors = [
            get_structural_feature_author_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_authors, current_row in zip(
            projects_data_authors,
            range(0, len(case_studies)),
        ):
            data_num_impl_authors = data_authors["num_implementing_authors"]
            avg_num_impl_authors = np.mean(data_num_impl_authors)
            rows[current_row].append(avg_num_impl_authors)

            var_num_impl_authors = np.var(data_num_impl_authors)
            rows[current_row].append(var_num_impl_authors)

            range_num_impl_authors = (
                min(data_num_impl_authors),
                max(data_num_impl_authors),
            )
            rows[current_row].append(range_num_impl_authors)

            corre_feature_size_num_implementing_authors, p_value = stats.pearsonr(
                data_authors["num_implementing_authors"],
                data_authors["feature_size"]
            )
            rows[current_row].extend([
                corre_feature_size_num_implementing_authors, p_value
            ])

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Avg Num Impl Authors",
                "Var Num Impl Authors",
                "Range Num Impl Authors",
                "Corr Ftr Size - Num Impl Authors",
                "P-Value",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class SFBRAuthorEvalTableGenerator(
    TableGenerator,
    generator_name="sfbr-author-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            SFBRAuthorEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class DFBRCommitEvalTable(Table, table_name="dfbr_commit_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_commits_specific = [
            get_commit_specific_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        projects_data_commits_general = [
            get_general_commit_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_commits, data_general, current_row in zip(
            projects_data_commits_specific,
            projects_data_commits_general,
            range(0, len(case_studies)),
        ):
            avg_interacting_features = np.mean(
                data_commits["num_interacting_features"]
            )
            rows[current_row].append(avg_interacting_features)

            avg_interacting_features_outside_df = np.mean(
                data_commits["num_interacting_features_outside_df"]
            )
            rows[current_row].append(avg_interacting_features_outside_df)

            fraction_commits_with_structural_interactions = data_general[
                "fraction_commits_structurally_interacting_with_features"][0]
            rows[current_row].append(
                fraction_commits_with_structural_interactions
            )

            num_commits = len(data_commits)
            fraction_all_commits = (
                len(
                    data_commits.loc[
                        data_commits["num_interacting_features"] > 0]
                ) / num_commits
            )
            rows[current_row].append(fraction_all_commits)

            commits_inside_df = data_commits.loc[
                data_commits["num_interacting_features_inside_df"] > 0]
            fraction_commits_inside_df = len(commits_inside_df) / num_commits
            rows[current_row].append(fraction_commits_inside_df)

            commits_outside_df = data_commits.loc[
                data_commits["num_interacting_features_outside_df"] > 0]
            fraction_commits_outside_df = len(commits_outside_df) / num_commits
            rows[current_row].append(fraction_commits_outside_df)

            commits_only_inside_df = commits_inside_df.loc[
                commits_inside_df["num_interacting_features_outside_df"] == 0]
            fraction_commits_only_inside_df = len(
                commits_only_inside_df
            ) / num_commits
            rows[current_row].append(fraction_commits_only_inside_df)

            commits_only_outside_df = commits_outside_df.loc[
                commits_outside_df["num_interacting_features_inside_df"] == 0]
            fraction_commits_only_outside_df = (
                len(commits_only_outside_df) / num_commits
            )
            rows[current_row].append(fraction_commits_only_outside_df)

            likelihood_coincide_structural_dataflow = data_general[
                "likelihood_dataflow_interaction_when_interacting_structurally"
            ][0]
            rows[current_row].append(likelihood_coincide_structural_dataflow)

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Avg Num Interacting Features",
                "Avg Num Interacting Features Outside DF",
                "Fraction Commits Structurally Interacting With Features",
                "Fraction Commits Interacting With Features Through DF",
                "Fraction Commits Interacting With Features Through Inside DF",
                "Fraction Commits Interacting With Features Through Outside DF",
                "Fraction Commits Interacting With Features Only Through Inside DF",
                "Fraction Commits Interacting With Features Only Through Outside DF",
                "Likelihood for Structural to Coincide With Dataflow Interaction",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of dataflow-based CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class DFBRCommitEvalTableGenerator(
    TableGenerator,
    generator_name="dfbr-commit-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            DFBRCommitEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class DFBRFeatureEvalTable(Table, table_name="dfbr_feature_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_features = [
            get_feature_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_features, current_row in zip(
            projects_data_features,
            range(0, len(case_studies)),
        ):
            corr_feature_size_num_interacting_commits_outside, p_value = stats.pearsonr(
                data_features["num_interacting_commits_outside_df"],
                data_features["feature_size"],
            )
            rows[current_row].extend([
                corr_feature_size_num_interacting_commits_outside, p_value
            ])

            corr_feature_size_num_interacting_commits_inside, p_value = stats.pearsonr(
                data_features["num_interacting_commits_inside_df"],
                data_features["feature_size"],
            )
            rows[current_row].extend([
                corr_feature_size_num_interacting_commits_inside, p_value
            ])

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 3),
            columns=[
                "Projects",
                "Corr Feature Size Num Interacting Commtis Outside DF",
                "P-Value",
                "Corr Feature Size Num Interacting Commtis Inside DF",
                "P-Value",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of dataflow-based CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class DFBRFeatureEvalTableGenerator(
    TableGenerator,
    generator_name="dfbr-feature-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            DFBRFeatureEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


class DFBRInterestingCommitsTable(
    Table, table_name="dfbr_interesting_commits_table"
):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs["case_study"]

        data = get_dataflow_data_for_case_study(case_study)

        rows = []

        data_points_with_many_interactions = data.loc[
            data["num_interacting_features"] >= 5]

        df = data_points_with_many_interactions
        df.sort_values(by=["part_of_feature"])

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["caption"
                  ] = f"Evaluation of project {case_study.project_name}. "
            kwargs["position"] = "t"

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
    options=[REQUIRE_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")
        return [
            DFBRInterestingCommitsTable(
                self.table_config, case_study=case_study, **self.table_kwargs
            )
        ]


class DFBRAuthorEvalTable(Table, table_name="dfbr_author_eval_table"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies: tp.List[CaseStudy] = self.table_kwargs["case_studies"]

        projects_data_authors = [
            get_dataflow_feature_author_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        rows = [[case_study.project_name] for case_study in case_studies] + [
            ["Mean"],
            ["Variance"],
        ]

        for data_authors, current_row in zip(
            projects_data_authors,
            range(0, len(case_studies)),
        ):
            data_num_interacting_authors = data_authors[
                "interacting_authors_outside"]
            avg_num_interacting_authors = np.mean(data_num_interacting_authors)
            rows[current_row].append(avg_num_interacting_authors)

            var_num_interacting_authors = np.var(data_num_interacting_authors)
            rows[current_row].append(var_num_interacting_authors)

            range_num_interacting_authors = (
                min(data_num_interacting_authors),
                max(data_num_interacting_authors),
            )
            rows[current_row].append(range_num_interacting_authors)
            print(data_authors)
            corre_feature_size_num_interacting_authors, p_value = stats.pearsonr(
                data_authors["interacting_authors_outside"],
                data_authors["feature_size"],
            )
            rows[current_row].extend([
                corre_feature_size_num_interacting_authors, p_value
            ])

        # calc overall mean and variance for each column
        add_mean_and_variance(rows, len(case_studies))

        df = pd.DataFrame(
            round_rows(rows, 2),
            columns=[
                "Projects",
                "Avg Num Interacting Authors",
                "Var Num Interacting Authors",
                "Range Num Interacting Authors",
                "Corr Ftr Size - Num Interacting Authors",
                "P-Value",
            ],
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        projects_separated_by_comma = ",".join([
            case_study.project_name for case_study in case_studies
        ])
        if table_format.is_latex():
            kwargs[
                "caption"
            ] = f"Evaluation of structural CFIs for projects {projects_separated_by_comma}. "
            kwargs["position"] = "t"

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )


class DFBRAuthorEvalTableGenerator(
    TableGenerator,
    generator_name="dfbr-author-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY],
):

    def generate(self) -> tp.List[Table]:
        case_studies: tp.List[CaseStudy] = self.table_kwargs.pop("case_study")
        return [
            DFBRAuthorEvalTable(
                self.table_config,
                case_studies=case_studies,
                **self.table_kwargs
            )
        ]


def round_rows(rows, digits) -> []:
    return [[
        entry if type(entry) is str else
        ((round(entry[0], digits), round(entry[1], digits))
         if type(entry) is tuple else round(entry, digits)) for entry in row
    ] for row in rows]


def add_mean_and_variance(rows, num_case_studies) -> None:
    for i in range(1, len(rows[0])):
        # column with ranges, need different computation
        if type(rows[0][i]) is tuple:
            list_vals_min = [rows[j][i][0] for j in range(0, num_case_studies)]
            list_vals_max = [rows[j][i][1] for j in range(0, num_case_studies)]
            rows[num_case_studies].append(
                (np.mean(list_vals_min), np.mean(list_vals_max))
            )
            rows[num_case_studies + 1].append(
                (np.var(list_vals_min), np.var(list_vals_max))
            )
            continue
        list_vals = [rows[j][i] for j in range(0, num_case_studies)]
        rows[num_case_studies].append(np.mean(list_vals))
        rows[num_case_studies + 1].append(np.var(list_vals))

import typing as tp

import matplotlib.pyplot as pyplot
import numpy as np
import pandas as pd
import seaborn as sns

from varats.data.reports.feature_blame_report import (
    StructuralFeatureBlameReport as SFBR,
)
from varats.data.reports.feature_blame_report import (
    DataflowFeatureBlameReport as DFBR,
)
from varats.data.reports.feature_blame_report import (
    generate_feature_scfi_data,
    generate_commit_scfi_data,
    generate_commit_specific_dcfi_data,
    generate_general_commit_dcfi_data,
    generate_feature_dcfi_data,
    generate_feature_author_scfi_data,
    generate_feature_author_dcfi_data,
)
from varats.jupyterhelper.file import (
    load_structural_feature_blame_report,
    load_dataflow_feature_blame_report,
)
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.project.project_util import get_local_project_gits
from varats.report.report import ReportFilepath
from varats.revision.revisions import get_processed_revisions_files
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.git_util import (
    num_active_commits,
    get_local_project_git_path,
    calc_repo_code_churn,
    ChurnConfig,
)


def get_structural_report_files_for_project(
    project_name: str,
) -> tp.List[ReportFilepath]:
    fnf = lambda x: "DFBR" in x
    report_files: tp.List[ReportFilepath] = get_processed_revisions_files(
        project_name=project_name,
        report_type=SFBR,
        file_name_filter=fnf,
        only_newest=False,
    )

    return report_files


def get_structural_feature_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    report_file = get_structural_report_files_for_project(case_study.project_name)[0]
    data_frame: pd.DataFrame = pd.DataFrame()
    report = load_structural_feature_blame_report(report_file)
    data_frame = generate_feature_scfi_data(report)
    return data_frame


def get_structural_commit_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    project_name = case_study.project_name

    report_file = get_structural_report_files_for_project(project_name)[0]

    report = load_structural_feature_blame_report(report_file)
    repo_lookup = get_local_project_gits(project_name)

    code_churn_lookup = {
        repo_name: calc_repo_code_churn(
            get_local_project_git_path(project_name, repo_name),
            ChurnConfig.create_c_style_languages_config(),
        )
        for repo_name, _ in repo_lookup.items()
    }

    data_frame = generate_commit_scfi_data(report, code_churn_lookup)

    return data_frame


######## STRUCTURAL #########


######## FEATURES #########


class FeatureSizeCorrSFBRPlot(Plot, plot_name="feature_size_corr_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        df = pd.concat(
            [
                get_structural_feature_data_for_case_study(case_study)
                for case_study in case_studies
            ]
        )

        plt = sns.regplot(data=df, x="feature_size", y="num_interacting_commits")

        plt.set(xlabel="Feature Size", ylabel="Number Interacting Commits")


class FeatureSizeCorrSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-corr-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeCorrSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureDisSFBRPlot(Plot, plot_name="feature_dis_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        dfs = [
            get_structural_feature_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        data = pd.concat(
            [
                df.assign(project=[case_study.project_name for _ in range(0, len(df))])
                for case_study, df in zip(case_studies, dfs)
            ]
        )

        plt = sns.boxplot(
            data=data,
            x="num_interacting_commits",
            y="project",
        )
        ticks = 5
        start = min(data["num_interacting_commits"])
        stop = max(data["num_interacting_commits"])
        step = round((stop - start) / ticks)
        plt.set_xticks(range(start, stop + step, step), range(start, stop + step, step))
        plt.set(
            xlabel="Number Interacting Commits",
            ylabel="Project",
            title="Structural Interactions of Features",
        )


class FeatureDisSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-dis-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureDisSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureSizeDisSFBRPlot(Plot, plot_name="feature_size_dis_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        df = pd.concat(
            [
                get_structural_feature_data_for_case_study(case_study)
                for case_study in case_studies
            ]
        )

        df = df.sort_values(by=["feature_size"])

        plt = sns.barplot(data=df, x="feature", y="feature_size", color="steelblue")
        plt.set(xlabel="Feature", ylabel="Size", title="")

        xticklabels = [str(i) for i in range(0, len(df))]
        plt.set(xticklabels=xticklabels)


class FeatureSizeDisSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-dis-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeDisSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


######## COMMITS #########


def get_pie_data_for_commit_data(commit_data) -> (tp.List[int], tp.List[int]):
    min_num_interacting_features = min(commit_data)
    max_num_interacting_features = max(commit_data)

    data = [
        0 for _ in range(min_num_interacting_features, max_num_interacting_features + 1)
    ]
    add_s = lambda x: "" if x == 1 else "s"
    labels = [
        "Impl. " + str(i) + " feature" + add_s(i)
        for i in range(min_num_interacting_features, max_num_interacting_features + 1)
    ]

    for num_interacting_features in commit_data:
        data[num_interacting_features - min_num_interacting_features] = (
            data[num_interacting_features - min_num_interacting_features] + 1
        )

    adj_labels, adj_data = ([], [])
    for i in range(0, max_num_interacting_features - min_num_interacting_features + 1):
        if data[i] == 0:
            continue
        frac = data[i] / len(commit_data)
        if frac < 0.05:
            num_interacting_features = i + min_num_interacting_features
            adj_labels.append(
                "Impl. >="
                + str(num_interacting_features)
                + " feature"
                + add_s(num_interacting_features)
            )
            adj_data.append(np.sum(data[i:]))
            break
        adj_labels.append(labels[i])
        adj_data.append(data[i])

    return (adj_data, adj_labels)


class CommitSFBRPieChart(Plot, plot_name="commit_sfbr_pie_chart"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        def func(pct):
            absolute = int(np.round(pct / 100.0 * len(commit_data)))
            return f"{absolute:d}"

        fig, naxs = pyplot.subplots(2, 2, figsize=(15, 15))
        case_study_counter = 0
        for axs in naxs:
            for ax in axs:
                case_study = case_studies[case_study_counter]
                commit_data = get_structural_commit_data_for_case_study(case_study).loc[
                    :, "num_interacting_features"
                ]
                data, labels = get_pie_data_for_commit_data(commit_data)
                explode = [0.1] + [0 for _ in range(1, len(data))]
                ax.pie(
                    data, labels=labels, explode=explode, autopct=lambda pct: func(pct)
                )
                ax.set_title(case_study.project_name)
                case_study_counter += 1


class CommitSFBRPieChartGenerator(
    PlotGenerator,
    generator_name="commit-sfbr-pie-chart",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            CommitSFBRPieChart(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class CommitSpecificSFBRPlot(Plot, plot_name="commit_specific_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        fig, naxs = pyplot.subplots(2, 2, figsize=(15, 15))
        case_study_counter = 0
        for axs in naxs:
            for nth_ax in axs:
                if case_study_counter == len(case_studies):
                    continue
                case_study = case_studies[case_study_counter]

                commit_data = get_structural_commit_data_for_case_study(case_study)
                commit_data = commit_data.sort_values(by=["num_interacting_features"])[
                    "num_interacting_features"
                ]

                interacting_with_nd1 = [
                    commit_data[index][0] for index in commit_data.index
                ]
                interacting_with_at_leat_nd2 = [
                    sum(commit_data[index][1:]) for index in commit_data.index
                ]
                stacked_commit_data = pd.DataFrame(
                    {
                        "Min Nesting Degree 1": interacting_with_nd1,
                        "Min Nesting Degree >=2": interacting_with_at_leat_nd2,
                    },
                    index=commit_data.index,
                )

                stacked_commit_data.plot.bar(stacked=True, width=0.95, ax=nth_ax)

                nth_ax.set_xlabel("Commits")
                nth_ax.set_ylabel("Num Interacting Features")
                step = round(len(commit_data) / 6)
                nth_ax.set_xticks(
                    ticks=[i * step for i in range(6)],
                    labels=[str(i * step) for i in range(6)],
                )
                nth_ax.set_title(case_study.project_name)
                case_study_counter += 1


class CommitSpecificSFBRPlotGenerator(
    PlotGenerator,
    generator_name="commit-specific-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            CommitSpecificSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


def get_stacked_proportional_commit_structural_data(
    case_studies: tp.List[CaseStudy],
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        data_commits = get_general_commit_dataflow_data_for_case_study(case_study)
        fraction_commits_implementing_features = data_commits[
            "fraction_commits_structurally_interacting_with_features"
        ][0]

        rows.append(
            [
                case_study.project_name,
                fraction_commits_implementing_features,
                1 - fraction_commits_implementing_features,
            ]
        )

    return pd.DataFrame(
        data=rows,
        columns=[
            "Projects",
            "Implementing Features",
            "Not Implementing Features",
        ],
    )


class CommitProportionalStructuralPlot(
    Plot, plot_name="commit_proportional_structural_plot"
):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = get_stacked_proportional_commit_structural_data(case_studies)
        data = data.sort_values(by=["Implementing Features"], ascending=True)
        print(data)
        plt = data.set_index("Projects").plot(
            kind="bar", stacked=True, ylabel="Proportional Commit Count"
        )
        plt.legend(title="Commit Kind", loc="center left", bbox_to_anchor=(1, 0.5))


class CommitProportionalStructuralPlotGenerator(
    PlotGenerator,
    generator_name="commit-proportional-structural-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            CommitProportionalStructuralPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


######## DATAFLOW #########


def get_dataflow_report_files_for_project(project_name: str) -> tp.List[ReportFilepath]:
    fnf = lambda x: not "DFBR" in x
    report_files: tp.List[ReportFilepath] = get_processed_revisions_files(
        project_name=project_name,
        report_type=DFBR,
        file_name_filter=fnf,
        only_newest=False,
    )

    return report_files


def get_both_reports_for_case_study(case_study: CaseStudy) -> tp.Tuple[SFBR, DFBR]:
    structural_report_file = get_structural_report_files_for_project(
        case_study.project_name
    )[0]
    dataflow_report_file = get_dataflow_report_files_for_project(
        case_study.project_name
    )[0]

    SFBRs: SFBR = load_structural_feature_blame_report(structural_report_file)
    DFBRs: DFBR = load_dataflow_feature_blame_report(dataflow_report_file)
    return (SFBRs, DFBRs)


def get_general_commit_dataflow_data_for_case_study(
    case_study: CaseStudy,
) -> pd.DataFrame:
    number_active_commits = num_active_commits(
        repo_folder=get_local_project_git_path(case_study.project_name)
    )
    SFBR, DFBR = get_both_reports_for_case_study(case_study)
    data_frame = generate_general_commit_dcfi_data(SFBR, DFBR, number_active_commits)

    return data_frame


def get_commit_specific_dataflow_data_for_case_study(
    case_study: CaseStudy,
) -> pd.DataFrame:
    number_active_commits = num_active_commits(
        repo_folder=get_local_project_git_path(case_study.project_name)
    )
    SFBR, DFBR = get_both_reports_for_case_study(case_study)
    data_frame = generate_commit_specific_dcfi_data(SFBR, DFBR, number_active_commits)

    return data_frame


######## COMMITS #########


class CommitDFBRPieChart(Plot, plot_name="commit_dfbr_pie_chart"):
    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        commit_data = get_specific_stacked_proportional_commit_dataflow_data(case_study)
        commit_data = commit_data.loc[commit_data["part_of_feature"] == 0]
        commit_data = commit_data.loc[commit_data["num_interacting_features"] > 0]
        commit_data = commit_data.loc[:, "num_interacting_features"]

        data, labels = get_pie_data_for_commit_data(commit_data)

        def func(pct):
            absolute = int(np.round(pct / 100.0 * len(commit_data)))
            return f"{absolute:d}"

        fig, ax = pyplot.subplots()
        ax.pie(data, labels=labels, autopct=lambda pct: func(pct))


class CommitDFBRPieChartGenerator(
    PlotGenerator,
    generator_name="commit-dfbr-pie-chart",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            CommitDFBRPieChart(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
            for case_study in case_studies
        ]


def get_specific_stacked_proportional_commit_dataflow_data(
    case_studies: tp.List[CaseStudy],
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        data_commits = get_commit_specific_dataflow_data_for_case_study(case_study)

        num_commits_with_df_int = len(
            data_commits.loc[data_commits["num_interacting_features"] > 0]
        )

        commits_inside_df = data_commits.loc[
            data_commits["num_interacting_features_inside_df"] > 0
        ]
        commits_only_inside_df = commits_inside_df.loc[
            commits_inside_df["num_interacting_features_outside_df"] == 0
        ]
        fraction_commits_only_inside_df = (
            len(commits_only_inside_df) / num_commits_with_df_int
        )

        commits_outside_df = data_commits.loc[
            data_commits["num_interacting_features_outside_df"] > 0
        ]
        commits_only_outside_df = commits_outside_df.loc[
            commits_outside_df["num_interacting_features_inside_df"] == 0
        ]
        fraction_commits_only_outside_df = (
            len(commits_only_outside_df) / num_commits_with_df_int
        )

        rows.append(
            [
                case_study.project_name,
                fraction_commits_only_outside_df,
                fraction_commits_only_inside_df,
                1 - fraction_commits_only_outside_df - fraction_commits_only_inside_df,
            ]
        )

    return pd.DataFrame(
        data=rows,
        columns=[
            "Projects",
            "Only Outside DF",
            "Only Inside DF",
            "Inside and Outside DF",
        ],
    )


class SpecificCommitProportionalDataflowPlot(
    Plot, plot_name="specific_commit_proportional_dataflow_plot"
):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = get_specific_stacked_proportional_commit_dataflow_data(case_studies)
        data = data.sort_values(by=["Inside and Outside DF"], ascending=True)
        print(data)
        plt = data.set_index("Projects").plot(
            kind="bar", stacked=True, ylabel="Proportional Commit Count"
        )
        plt.legend(title="Commit Kind", loc="center left", bbox_to_anchor=(1, 0.5))


class SpecificProportionalDataflowPlotGenerator(
    PlotGenerator,
    generator_name="specific-commit-proportional-dataflow-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            SpecificCommitProportionalDataflowPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


def get_general_stacked_proportional_commit_dataflow_data(
    case_studies: tp.List[CaseStudy],
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        data_commits = get_commit_specific_dataflow_data_for_case_study(case_study)
        num_commits = len(data_commits)

        fraction_commits_with_df_int = (
            len(data_commits.loc[data_commits["num_interacting_features"] > 0])
            / num_commits
        )

        rows.append(
            [
                case_study.project_name,
                fraction_commits_with_df_int,
                1 - fraction_commits_with_df_int,
            ]
        )

    return pd.DataFrame(
        data=rows,
        columns=[
            "Projects",
            "Commits With DF Interactions",
            "Commits Without DF Interactions",
        ],
    )


class GeneralCommitProportionalDataflowPlot(
    Plot, plot_name="general_commit_proportional_dataflow_plot"
):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = get_general_stacked_proportional_commit_dataflow_data(case_studies)
        data = data.sort_values(by=["Commits With DF Interactions"], ascending=True)
        print(data)
        plt = data.set_index("Projects").plot(
            kind="bar",
            stacked=True,
            ylabel="Proportional Commit Count",
            color=["red", "blue"],
        )
        plt.legend(title="Commit Kind", loc="center left", bbox_to_anchor=(1, 0.5))


class GeneralProportionalDataflowPlotGenerator(
    PlotGenerator,
    generator_name="general-commit-proportional-dataflow-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            GeneralCommitProportionalDataflowPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


######## FEATURES #########


def get_feature_dataflow_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    SFBRs, DFBRs = get_both_reports_for_case_study(case_study)
    data_frame = generate_feature_dcfi_data(SFBRs, DFBRs)

    return data_frame


class FeatureSizeCorrDFBRPlot(Plot, plot_name="feature_size_corr_dfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = pd.concat(
            [
                get_feature_dataflow_data_for_case_study(case_study)
                for case_study in case_studies
            ]
        )
        print(data)
        plt = sns.regplot(
            data=data, x="feature_size", y="num_interacting_commits_outside_df"
        )
        plt.set(
            xlabel="Feature Size",
            ylabel="Number of Interacting Commits not Part of Features",
        )


class FeatureSizeCorrDFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-corr-dfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeCorrDFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureDisDFBRPlot(Plot, plot_name="feature_dis_dfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        dfs = [
            get_feature_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ]
        data = pd.concat(
            [
                get_feature_dataflow_data_for_case_study(case_study)
                for case_study in case_studies
            ]
        )
        data = data.sort_values(by=["num_interacting_commits_outside_df"])
        pyplot.figure(figsize=(10.3, 6))
        ax = sns.barplot(
            data=data,
            x="feature",
            y="num_interacting_commits_outside_df",
            color="blue",
            palette=["tab:blue"],
        )
        ax.set_xlabel("Feature", size="11")
        ax.set_ylabel("Number of Interacting Outside Commits", size="12")
        ax.set_title("Feature Commit Dataflow Interactions from Outisde", size="14")
        return None

        fig, naxs = pyplot.subplots(2, 2, figsize=(22, 22))
        case_study_counter = 0
        for axs in naxs:
            for ax in axs:
                case_study = case_studies[case_study_counter]
                df = get_feature_dataflow_data_for_case_study(case_study)
                df = df.sort_values(by=["num_interacting_commits_outside_df"])
                print(df)
                sns.barplot(
                    data=df,
                    x="feature",
                    y="num_interacting_commits_outside_df",
                    ax=ax,
                    color="blue",
                    palette=["tab:blue"],
                )
                ax.set_xlabel("Feature", size="16")
                ax.set_ylabel("Number of Interacting Outside Commits", size="16")
                ax.set_title(case_study.project_name, size="22")
                case_study_counter += 1

        fig.suptitle(
            "Dataflow Interactions from Outside of Features"
            + " for Projects "
            + ",".join([case_study.project_name for case_study in case_studies]),
            size="26",
        )


class FeatureDisDFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-dis-dfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureDisDFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


########## AUTHORS ###########


def get_structural_feature_author_data_for_case_study(
    case_study: CaseStudy,
) -> pd.DataFrame:
    report_file = get_structural_report_files_for_project(case_study.project_name)[0]
    project_gits = get_local_project_gits(case_study.project_name)
    report = load_structural_feature_blame_report(report_file)
    data_frame: pd.DataFrame = generate_feature_author_scfi_data(report, project_gits)

    return data_frame


def get_dataflow_feature_author_data_for_case_study(
    case_study: CaseStudy,
) -> pd.DataFrame:
    structural_report_file = get_structural_report_files_for_project(
        case_study.project_name
    )[0]
    dataflow_report_file = get_dataflow_report_files_for_project(
        case_study.project_name
    )[0]
    project_gits = get_local_project_gits(case_study.project_name)
    structural_report = load_structural_feature_blame_report(structural_report_file)
    dataflow_report = load_dataflow_feature_blame_report(dataflow_report_file)
    data_frame: pd.DataFrame = generate_feature_author_dcfi_data(
        structural_report, dataflow_report, project_gits
    )

    return data_frame


def get_stacked_author_data_for_case_studies(
    case_studies: tp.List[CaseStudy],
    projects_data,
) -> pd.DataFrame:
    rows = []

    max_num_interacting_authors = max(
        [max(project_data) for project_data in projects_data]
    )

    for case_study, project_data in zip(case_studies, projects_data):
        count: [int] = [0 for _ in range(0, max_num_interacting_authors)]
        for num_interacting_authors in project_data:
            count[num_interacting_authors - 1] = count[num_interacting_authors - 1] + 1

        rows.append([case_study.project_name] + count)

    author_columns, adj_rows = (
        [],
        [[case_study.project_name] for case_study in case_studies],
    )
    for i in range(1, max_num_interacting_authors + 1):
        s = np.sum([int(rows[j][i]) for j in range(0, len(case_studies))])
        if s > 0:
            author_columns.append(str(i) + " Author" + ("s" if i > 1 else ""))
            for j in range(0, len(case_studies)):
                adj_rows[j].append(rows[j][i])
    return pd.DataFrame(adj_rows, columns=["Project"] + author_columns)


class FeatureAuthorStructDisPlot(Plot, plot_name="feature_author_struct_dis_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        fig, axs = pyplot.subplots(ncols=len(case_studies), figsize=(15, 3))
        counter = 0
        for ax, case_study in zip(axs, case_studies):
            author_data = get_structural_feature_author_data_for_case_study(case_study)
            author_data = author_data.sort_values(by=["num_implementing_authors"])
            sns.barplot(
                data=author_data,
                x="feature",
                y="num_implementing_authors",
                color="tab:blue",
                ax=ax,
            )
            if counter == 0:
                ax.set_xlabel("Features")
                ax.set_ylabel("Num Implementing Authors")
            else:
                ax.set_xlabel("")
                ax.set_ylabel("")
            x_rng = range(0, len(author_data), 2)
            ax.set_xticks(ticks=x_rng, labels=[str(i) for i in x_rng])
            max_impl_authors = max(author_data["num_implementing_authors"])
            y_rng = range(1, max_impl_authors + 1)
            ax.set_yticks(ticks=y_rng, labels=[str(i) for i in y_rng])
            ax.set_title(case_study.project_name)
            counter += 1


class FeatureAuthorStructDisPlotGenerator(
    PlotGenerator,
    generator_name="feature-author-struct-dis-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            FeatureAuthorStructDisPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureAuthorDataflowDisPlot(Plot, plot_name="feature_author_dataflow_dis_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        projects_data = [
            get_dataflow_feature_author_data_for_case_study(case_study).loc[
                :, "interacting_authors_outside"
            ]
            for case_study in case_studies
        ]
        data = get_stacked_author_data_for_case_studies(case_studies, projects_data)

        data = data.sort_values(by=["1 Author"])
        print(data)
        data.set_index("Project").plot(
            kind="bar",
            stacked=True,
            ylabel="Number of Features Affected Through Outside Dataflow by",
        )


class FeatureAuthorDataflowDisPlotGenerator(
    PlotGenerator,
    generator_name="feature-author-dataflow-dis-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            FeatureAuthorDataflowDisPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


def get_combined_author_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    structural_data = get_structural_feature_author_data_for_case_study(case_study)
    structural_data = structural_data.sort_values(by=["num_implementing_authors"])
    dataflow_data = get_dataflow_feature_author_data_for_case_study(case_study)

    combined_rows = []
    for i in structural_data.index:
        feature = structural_data.loc[i, "feature"]
        num_implementing_authors = structural_data.loc[i, "num_implementing_authors"]
        for _ in range(num_implementing_authors):
            combined_rows.append(
                [
                    feature,
                    "Implementing Authors",  # type
                ]
            )
    for i in dataflow_data.index:
        feature = dataflow_data.loc[i, "feature"]
        interacting_authors_outside = dataflow_data.loc[
            i, "interacting_authors_outside"
        ]
        for _ in range(interacting_authors_outside):
            combined_rows.append(
                [
                    feature,
                    "Interacting Authors Through Outside Dataflow",  # type
                ]
            )

    columns = ["feature", "interaction_type"]

    return pd.DataFrame(combined_rows, columns=columns)


class FeatureCombinedAuthorPlot(Plot, plot_name="feature_combined_author_plot"):
    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        data = get_combined_author_data_for_case_study(case_study)
        print(data)
        pyplot.figure(figsize=(13, 8))
        sns.histplot(
            data=data,
            x="feature",
            hue="interaction_type",
            multiple="dodge",
            shrink=0.8,
        )


class FeatureCombinedAuthorPlotGenerator(
    PlotGenerator,
    generator_name="feature-combined-author-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureCombinedAuthorPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
            for case_study in case_studies
        ]


class FeatureSizeCorrAuthorPlot(Plot, plot_name="feature_size_corr_author_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = pd.concat(
            [
                get_structural_feature_author_data_for_case_study(case_study)
                for case_study in case_studies
            ]
        )
        print(data)
        ax = sns.regplot(data=data, x="feature_size", y="num_implementing_authors")
        ax.set(xlabel="Feature Size", ylabel="Number Implementing Authors")


class FeatureSizeCorrAuthorPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-corr-author-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeCorrAuthorPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]

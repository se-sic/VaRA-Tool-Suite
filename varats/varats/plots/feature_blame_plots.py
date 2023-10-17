import typing as tp

import matplotlib.pyplot as pyplot
import matplotlib.gridspec as SubplotSpec
from scipy import stats
import numpy as np
import pandas as pd
import seaborn as sns

from varats.data.metrics import apply_tukeys_fence
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
    generate_feature_author_data,
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


class FeatureSFBRPlot(Plot, plot_name="feature_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        fig, naxs = pyplot.subplots(len(case_studies), 3, figsize=(18, 18))
        for ax, case_study in zip(naxs[:, 0], case_studies):
            ax.annotate(
                case_study.project_name,
                xy=(0, 0.5),
                xytext=(-ax.yaxis.labelpad - 10, 0),
                xycoords=ax.yaxis.label,
                textcoords="offset points",
                size="20",
                ha="right",
                va="center",
            )
        fig.tight_layout(pad=5)
        row: int = 1
        for axs, case_study in zip(naxs, case_studies):
            data = get_structural_feature_data_for_case_study(case_study)

            data = data.sort_values(by=["num_interacting_commits_nd1"])

            stacked_feature_data = pd.DataFrame(
                {
                    "Interacting with ND1": data["num_interacting_commits_nd1"].values,
                    "Interacting with ND>1": data[
                        "num_interacting_commits_nd>1"
                    ].values,
                },
                index=data["feature"].values,
            )

            stacked_feature_data.plot.bar(stacked=True, width=0.95, ax=axs[0])

            axs[0].set_xlabel("Features" if row == 1 else "", size="13")
            axs[0].set_ylabel("Num Interacting Commits", size="13")
            axs[0].set_xticklabels(data["feature"].values, rotation=(22.5), ha="right")
            if row > 1:
                axs[0].legend_.remove()

            data = data.sort_values(by=["def_feature_size"])

            stacked_feature_size_data = pd.DataFrame(
                {
                    "Definite Feature Size": data["def_feature_size"].values,
                    "Potential Feature Size": data["pot_feature_size"].values
                    - data["def_feature_size"].values,
                },
                index=data["feature"].values,
            )

            stacked_feature_size_data.plot.bar(stacked=True, width=0.95, ax=axs[1])

            axs[1].set_ylabel("Feature Size", size="13")
            axs[1].set_xticklabels(data["feature"].values, rotation=(22.5), ha="right")
            if row > 1:
                axs[1].legend_.remove()

            sns.regplot(
                data=data,
                x="def_feature_size",
                y="num_interacting_commits_nd1",
                ax=axs[2],
                ci=None,
                label="Commits with ND1, Def Ftr Size",
            )
            sns.regplot(
                data=data,
                x="pot_feature_size",
                y="num_interacting_commits",
                ax=axs[2],
                ci=None,
                color="#997B59",
                label="Any commit, Pot Ftr Size",
            )
            if row == 1:
                axs[2].legend(ncol=1)

            axs[2].set_xlabel("Feature Size", size="13")
            axs[2].set_ylabel("Num Interacting Commits", size="13")
            max_ftr_size = max(data["pot_feature_size"].values)
            max_int_cmmts = max(data["num_interacting_commits"].values)
            corr, p_value = stats.pearsonr(
                data["num_interacting_commits_nd1"].values,
                data["def_feature_size"].values,
            )
            axs[2].text(
                max_ftr_size * 0.5,
                max_int_cmmts * 0.11,
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:blue",
            )
            corr, p_value = stats.pearsonr(
                data["num_interacting_commits"].values,
                data["pot_feature_size"].values,
            )
            axs[2].text(
                max_ftr_size * 0.5,
                max_int_cmmts * 0.02,
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="#997B59",
            )

            row += 1

        fig.subplots_adjust(left=0.15, top=0.95)


class FeatureSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


######## COMMITS #########


class CommitSFBRPlot(Plot, plot_name="commit_sfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        fig, naxs = pyplot.subplots(2, 2, figsize=(18, 18))
        projects_commit_data = [
            get_structural_commit_data_for_case_study(case_study)
            for case_study in case_studies
        ]

        case_study_counter = 0
        max_count = max(
            [
                sum(
                    [
                        sum(commit_data.at[index, "num_interacting_features"]) == 1
                        for index in commit_data.index
                    ]
                )
                for commit_data in projects_commit_data
            ]
        )
        max_num_interacting_features = max(
            [
                max(
                    [
                        sum(commit_data.at[index, "num_interacting_features"])
                        for index in commit_data.index
                    ]
                )
                for commit_data in projects_commit_data
            ]
        )
        for axs in naxs:
            for ax in axs:
                case_study = case_studies[case_study_counter]
                commit_data = projects_commit_data[case_study_counter]
                rows = []
                for index in commit_data.index:
                    num_interacting_features = sum(
                        commit_data.at[index, "num_interacting_features"]
                    )
                    rows.append(
                        [
                            num_interacting_features,
                            num_interacting_features == 1,
                        ]
                    )
                df = pd.DataFrame(
                    data=rows,
                    columns=[
                        "Num Interacting Features",
                        "Changing More Than One Feature",
                    ],
                )
                sns.histplot(
                    data=df,
                    y="Num Interacting Features",
                    discrete=True,
                    ax=ax,
                    hue="Changing More Than One Feature",
                    palette=[
                        "tab:orange",
                        "tab:blue",
                    ],
                )
                ax.legend_.remove()
                ax.set_title(case_study.project_name, size="18")
                ax.set_xlabel("Count", size="15")
                ax.set_ylabel("Num Interacting Features", size="15")
                ax.set_xticks(range(0, max_count + 1, 10))
                ax.set_xticklabels(range(0, max_count + 1, 10))
                ax.set_yticks(range(1, max_num_interacting_features + 1, 1))
                ax.set_yticklabels(range(1, max_num_interacting_features + 1, 1))
                case_study_counter += 1


class CommitSFBRPlotGenerator(
    PlotGenerator,
    generator_name="commit-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            CommitSFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


def get_stacked_proportional_commit_structural_data(
    case_studies: tp.List[CaseStudy], num_active_commits_cs: tp.Dict[str, int]
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        number_active_commits = num_active_commits_cs.get(case_study.project_name)
        data_commits = get_general_commit_dataflow_data_for_case_study(
            case_study, number_active_commits
        )
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
            "Structurally Interacting With Features",
            "Not Structurally Interacting With Features",
        ],
    )


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
    case_study: CaseStudy, number_active_commits
) -> pd.DataFrame:
    SFBR, DFBR = get_both_reports_for_case_study(case_study)
    data_frame = generate_general_commit_dcfi_data(SFBR, DFBR, number_active_commits)

    return data_frame


def get_commit_specific_dataflow_data_for_case_study(
    case_study: CaseStudy,
    number_active_commits: int,
) -> pd.DataFrame:
    SFBR, DFBR = get_both_reports_for_case_study(case_study)
    data_frame = generate_commit_specific_dcfi_data(SFBR, DFBR, number_active_commits)

    return data_frame


######## COMMITS #########


def get_combined_stacked_proportional_commit_dataflow_data(
    case_studies: tp.List[CaseStudy],
    num_active_commits_cs: tp.Dict[str, int],
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        number_active_commits = num_active_commits_cs.get(case_study.project_name)
        dataflow_data = get_commit_specific_dataflow_data_for_case_study(
            case_study, number_active_commits
        )
        num_df_int_commits = len(
            dataflow_data.loc[dataflow_data["num_interacting_features"] > 0]
        )

        fraction_commits_with_df_int = num_df_int_commits / number_active_commits

        structural_data = get_structural_commit_data_for_case_study(case_study)
        num_struct_int_commits = len(structural_data)

        fraction_commits_with_struct_int = (
            num_struct_int_commits / number_active_commits
        )

        rows.extend(
            [
                [
                    case_study.project_name,
                    fraction_commits_with_df_int * 100,
                    "Dataflow",
                ],
                [
                    case_study.project_name,
                    fraction_commits_with_struct_int * 100,
                    "Structural",
                ],
            ]
        )

    return pd.DataFrame(
        data=rows,
        columns=[
            "Projects",
            "Proportion",
            "Interaction Type",
        ],
    )


def get_specific_stacked_proportional_commit_dataflow_data(
    case_studies: tp.List[CaseStudy],
    num_active_commits_cs: tp.Dict[str, int],
) -> pd.DataFrame:
    rows = []
    for case_study in case_studies:
        number_active_commits = num_active_commits_cs.get(case_study.project_name)
        data_commits = get_commit_specific_dataflow_data_for_case_study(
            case_study, number_active_commits
        )

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

        commits_inside_and_outside_df = commits_inside_df.loc[
            commits_inside_df["num_interacting_features_outside_df"] > 0
        ]
        fraction_commits_inside_and_outside_df = (
            len(commits_inside_and_outside_df) / num_commits_with_df_int
        )

        rows.append(
            [
                case_study.project_name,
                fraction_commits_only_outside_df * 100,
                fraction_commits_inside_and_outside_df * 100,
                fraction_commits_only_inside_df * 100,
            ]
        )

    return pd.DataFrame(
        data=rows,
        columns=[
            "Projects",
            "Only Outside DF",
            "Outside and Inside DF",
            "Only Inside DF",
        ],
    )


class ProportionalCommitDFBRPlot(Plot, plot_name="proportional_commit_dfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        num_active_commits_cs: tp.Dict[str, int] = {
            "xz": 1039,
            "gzip": 194,
            "bzip2": 37,
            "lrzip": 717,
        }
        """
        for case_study in case_studies:
            num_active_commits_cs.update(
                {
                    case_study.project_name: num_active_commits(
                        repo_folder=get_local_project_git_path(case_study.project_name)
                    )
                }
            )
        """
        print(num_active_commits_cs)
        fig, ((ax_0, ax_1)) = pyplot.subplots(nrows=1, ncols=2, figsize=(12, 7))

        data = get_combined_stacked_proportional_commit_dataflow_data(
            case_studies, num_active_commits_cs
        )
        data = data.sort_values(by=["Proportion"], ascending=True)
        print(data)
        sns.barplot(
            data=data,
            x="Projects",
            y="Proportion",
            hue="Interaction Type",
            palette=["tab:gray", "tab:red"],
            ax=ax_0,
        )
        for container in ax_0.containers:
            ax_0.bar_label(container, fmt="%.1f%%")
        ax_0.set_title("Active Commits Interacting With Features")
        ax_0.set_ylabel("Proportion (%)")

        case_studies = [
            case_studies[0],
            case_studies[2],
            case_studies[1],
        ]
        data = get_specific_stacked_proportional_commit_dataflow_data(
            case_studies, num_active_commits_cs
        )
        # data = data.sort_values(by=["Only Outside DF"], ascending=False)
        print(data)
        plt = data.set_index("Projects").plot(
            kind="bar", stacked=True, ylabel="Proportion (%)", ax=ax_1
        )
        plt.legend(title="Dataflow Origin", loc="center left", bbox_to_anchor=(1, 0.5))
        ax_1.bar_label(ax_1.containers[0], fmt="%.1f%%")
        ax_1.bar_label(ax_1.containers[1], fmt="%.1f%%")
        ax_1.set_xticklabels(data["Projects"].values, rotation=(0))
        ax_1.set_title("Dataflow Origin for Commits")


class ProportionalCommitDFBRPlotGenerator(
    PlotGenerator,
    generator_name="proportional-commit-dfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[case_studies] = self.plot_kwargs["case_study"]
        return [
            ProportionalCommitDFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


######## FEATURES #########


def get_feature_dataflow_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    SFBRs, DFBRs = get_both_reports_for_case_study(case_study)
    data_frame = generate_feature_dcfi_data(SFBRs, DFBRs)

    return data_frame


class FeatureDFBRPlot(Plot, plot_name="feature_dfbr_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        fig, naxs = pyplot.subplots(nrows=len(case_studies), ncols=3, figsize=(17, 17))
        for ax, case_study in zip(naxs[:, 0], case_studies):
            ax.annotate(
                case_study.project_name,
                xy=(0, 0.5),
                xytext=(-ax.yaxis.labelpad - 10, 0),
                xycoords=ax.yaxis.label,
                textcoords="offset points",
                size="20",
                ha="right",
                va="center",
            )
        fig.tight_layout(pad=5)
        row: int = 1
        pos: tp.List[tp.Tuple[int]] = [
            (0.01, 0.8),
            (0.4, 0.1),
            (0.01, 0.99),
            (0.03, 0.99),
        ]
        for axs, case_study in zip(naxs, case_studies):
            data = get_feature_dataflow_data_for_case_study(case_study)
            data = data.sort_values(by=["feature_size"])
            rows = []
            for index in data.index:
                feature = data.at[index, "feature"]
                rows.extend(
                    [
                        [
                            feature,
                            data.at[index, "num_interacting_commits_outside_df"],
                            "Outside Commits",
                        ],
                        [
                            feature,
                            data.at[index, "num_interacting_commits_inside_df"],
                            "Inside Commits",
                        ],
                    ]
                )
            df = pd.DataFrame(
                data=rows,
                columns=["Feature", "Num Interacting Commits", "Commit Kind"],
            )
            sns.barplot(
                data=df,
                x="Feature",
                y="Num Interacting Commits",
                hue="Commit Kind",
                ax=axs[0],
            )
            axs[0].axhline(
                y=np.mean(data["num_interacting_commits_outside_df"].values),
                color="tab:blue",
                linestyle="--",
                linewidth=2,
            )
            axs[0].axhline(
                y=np.mean(data["num_interacting_commits_inside_df"].values),
                color="tab:orange",
                linestyle="--",
                linewidth=2,
            )
            axs[0].set_xlabel("Features (Sorted by Size)" if row==1 else "", size=13)
            axs[0].set_ylabel("Num Interacting Commits", size=13)
            axs[0].set_xticklabels(
                labels=data["feature"].values, rotation=(22.5), ha="right"
            )

            if row > 1:
                axs[0].legend_.remove()

            df = pd.DataFrame(
                data=[
                    [   
                        data.at[index, "feature_size"],
                        data.at[index, "num_interacting_commits_outside_df"]
                        / data.at[index, "num_interacting_commits_inside_df"],
                    ]
                    for index in data.index
                ],
                columns=["Feature Size", "Proportion Outside to Inside Commits"],
            )
            sns.regplot(
                data=df,
                x="Feature Size",
                y="Proportion Outside to Inside Commits",
                ci=None,
                ax=axs[1],
                label="Outside Commits",
            )
            max_ftr_size = max(df["Feature Size"].values)
            max_proportion = max(df["Proportion Outside to Inside Commits"].values)
            corr, p_value = stats.pearsonr(
                df["Feature Size"].values,
                df["Proportion Outside to Inside Commits"].values,
            )
            axs[1].text(
                max_ftr_size * 0.35,
                max_proportion * 0.95,
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:blue",
            )
            axs[1].set_xlabel("Feature Size", size=13)
            axs[1].set_ylabel("Proportion Outside to Inside Commits", size=11)


            sns.regplot(
                data=data,
                x="feature_size",
                y="num_interacting_commits_outside_df",
                ci=None,
                ax=axs[2],
                line_kws={"lw": 2},
                scatter=True,
                truncate=False,
                label="Outside Commits",
            )
            sns.regplot(
                data=data,
                x="feature_size",
                y="num_interacting_commits_inside_df",
                ci=None,
                ax=axs[2],
                line_kws={"lw": 2},
                scatter=True,
                truncate=False,
                label="Inside Commits",
            )
            axs[2].set_xlabel("Feature Size", size=13)
            axs[2].set_ylabel("Num Interacting Commits", size=13)
            if row == 1:
                axs[2].legend(ncol=1)

            max_int_cmmts = max(
                [
                    max(data["num_interacting_commits_outside_df"].values),
                    max(data["num_interacting_commits_inside_df"].values),
                ]
            )
            corr, p_value = stats.pearsonr(
                data["num_interacting_commits_outside_df"].values,
                data["feature_size"].values,
            )
            axs[2].text(
                max_ftr_size * pos[row - 1][0],
                max_int_cmmts * pos[row - 1][1],
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:blue",
            )
            corr, p_value = stats.pearsonr(
                data["num_interacting_commits_inside_df"].values,
                data["feature_size"].values,
            )
            axs[2].text(
                max_ftr_size * pos[row - 1][0],
                max_int_cmmts * (pos[row - 1][1] - 0.07),
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:orange",
            )

            row += 1

        fig.subplots_adjust(left=0.15, top=0.95)


class FeatureDFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-dfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureDFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


########## AUTHORS ###########


def get_feature_author_data_for_case_study(
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
    data_frame: pd.DataFrame = generate_feature_author_data(
        structural_report, dataflow_report, project_gits
    )

    return data_frame


class AuthorCFIPlot(Plot, plot_name="author_cfi_plot"):
    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        fig, naxs = pyplot.subplots(nrows=len(case_studies), ncols=2, figsize=(15, 15))
        for ax, case_study in zip(naxs[:, 0], case_studies):
            ax.annotate(
                case_study.project_name,
                xy=(0, 0.5),
                xytext=(-ax.yaxis.labelpad - 10, 0),
                xycoords=ax.yaxis.label,
                textcoords="offset points",
                size="20",
                ha="right",
                va="center",
            )
        fig.tight_layout(pad=5)
        row: int = 1
        corr_x_pos = [0, 600, 20, 15]
        corr_y_pos = [(1.9, 1.83), (1.8, 1.2), (2.5, 2.35), (5.6, 5.2)]
        for axs, case_study in zip(naxs, case_studies):
            data = get_feature_author_data_for_case_study(case_study)
            data = data.sort_values(by=["feature_size"])

            rows = []
            for index in data.index:
                feature = data.at[index, "feature"]
                rows.extend(
                    [
                        [
                            feature,
                            data.at[index, "struct_authors"],
                            "Structural",
                        ],
                        [
                            feature,
                            data.at[index, "df_authors"],
                            "Outside DF",
                        ],
                        [
                            feature,
                            data.at[index, "unique_df_authors"],
                            "Unique DF",
                        ],
                    ]
                )
            df = pd.DataFrame(
                data=rows,
                columns=["Feature", "Num Interacting Authors", "Author Type"],
            )
            sns.barplot(
                data=df,
                x="Feature",
                y="Num Interacting Authors",
                hue="Author Type",
                ax=axs[0],
            )
            axs[0].set_xlabel("Features (sorted by size)" if row == 1 else "", size=13)
            axs[0].set_ylabel("Num Interacting Authors", size=13)
            axs[0].set_xticklabels(
                labels=data["feature"].values, rotation=(22.5), ha="right"
            )
            y_tick_range = range(0, max(df["Num Interacting Authors"].values + 1))
            axs[0].set_yticks(
                y_tick_range
            )
            axs[0].set_yticklabels(
                y_tick_range
            )

            sns.regplot(
                data=data,
                x="feature_size",
                y="struct_authors",
                ci=None,
                ax=axs[1],
                label="Structural Interactions",
            )
            sns.regplot(
                data=data,
                x="feature_size",
                y="df_authors",
                ci=None,
                ax=axs[1],
                label="(Outside) Dataflow Interactions",
            )
            axs[1].set_xlabel("Feature Size", size=13)
            axs[1].set_ylabel("Num Interacting Authors", size=13)
            axs[1].set_yticks(
                y_tick_range
            )
            axs[1].set_yticklabels(
                y_tick_range
            )
            axs[1].legend(ncol=1)

            corr, p_value = stats.pearsonr(
                data["struct_authors"].values,
                data["feature_size"].values,
            )
            axs[1].text(
                corr_x_pos[row - 1],
                corr_y_pos[row - 1][0],
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:blue",
            )
            corr, p_value = stats.pearsonr(
                data["df_authors"].values,
                data["feature_size"].values,
            )
            axs[1].text(
                corr_x_pos[row - 1],
                corr_y_pos[row - 1][1],
                "corr=" + str(round(corr, 3)) + ", p-value=" + str(round(p_value, 3)),
                color="tab:orange",
            )

            row += 1

        fig.subplots_adjust(left=0.15, top=0.95)


class AuthorCFIPlotGenerator(
    PlotGenerator,
    generator_name="author-cfi-plot",
    options=[REQUIRE_MULTI_CASE_STUDY],
):
    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            AuthorCFIPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]

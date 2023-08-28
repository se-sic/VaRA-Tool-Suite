import typing as tp

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
    generate_commit_dcfi_data,
    generate_feature_dcfi_data,
    generate_feature_author_scfi_data,
)
from varats.jupyterhelper.file import (
    load_structural_feature_blame_report,
    load_dataflow_feature_blame_report,
)
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
)
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)
from varats.utils.git_util import (
    num_commits,
    num_active_commits,
    get_local_project_git_path,
)


def get_structural_report_files_for_project(
    project_name: str
) -> tp.Tuple[tp.List[ReportFilepath], tp.List[ReportFilepath]]:
    fnf = lambda x: "DFBR" in x
    report_files: tp.List[ReportFilepath] = get_processed_revisions_files(
        project_name=project_name,
        report_type=SFBR,
        file_name_filter=fnf,
        only_newest=False
    )

    failed_report_files: tp.List[ReportFilepath] = get_failed_revisions_files(
        project_name=project_name,
        report_type=SFBR,
        file_name_filter=fnf,
        only_newest=False
    )

    return report_files, failed_report_files


def get_structural_feature_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:
    report_files, failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    data_frame: pd.DataFrame = pd.DataFrame()
    report = load_structural_feature_blame_report(report_files[0])
    data_frame = generate_feature_scfi_data(report)
    return data_frame


def get_structural_commit_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:
    report_files, failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    data_frame: pd.DataFrame = pd.DataFrame()
    report = load_structural_feature_blame_report(report_files[0])
    data_frame = generate_commit_scfi_data(report)

    return data_frame


class FeatureSizeCorrSFBRPlot(Plot, plot_name="feature_size_corr_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        df = pd.concat([
            get_structural_feature_data_for_case_study(case_study)
            for case_study in case_studies
        ])

        plt = sns.regplot(
            data=df, x='feature_size', y='num_interacting_commits'
        )

        plt.set(xlabel="Feature Size", ylabel="Number Interacting Commits")


class FeatureSizeCorrSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-corr-sfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
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
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_feature_data_for_case_study(case_study)

        plt = sns.catplot(data=df, x='num_interacting_commits', kind="box")

        plt.set(
            xlabel="Number Interacting Commits",
            ylabel=case_study.project_name,
            title="Structural Interactions of Features"
        )


class FeatureDisSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-dis-sfbr-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureDisSFBRPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


class FeatureSizeDisSFBRPlot(Plot, plot_name="feature_size_dis_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_feature_data_for_case_study(case_study)

        df = df.sort_values(by=['feature_size'])
        print(df)
        plt = sns.barplot(
            data=df, x='feature', y='feature_size', color='steelblue'
        )
        plt.set(xlabel="Feature", ylabel="Size", title="Feature Sizes in XZ")

        xticklabels = [
            df['feature'][i] if i % 2 == 1 else "" for i in range(0, len(df))
        ]
        plt.set(xticklabels=xticklabels)


class FeatureSizeDisSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-dis-sfbr-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeDisSFBRPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


class CommitDisSFBRPlot(Plot, plot_name="commit_dis_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_commit_data_for_case_study(case_study)

        plt = sns.histplot(
            data=df, x='num_interacting_features', binwidth=1, kde=True
        )

        plt.set(
            xlabel="Number Interacting Features",
            ylabel="Commit Count",
            title="Structural Interactions of Commits"
        )


class CommitDisSFBRPlotGenerator(
    PlotGenerator,
    generator_name="commit-dis-sfbr-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            CommitDisSFBRPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


######## DATAFLOW #########


def get_dataflow_report_files_for_project(
    project_name: str
) -> tp.Tuple[tp.List[ReportFilepath], tp.List[ReportFilepath]]:
    fnf = lambda x: not "DFBR" in x
    report_files: tp.List[ReportFilepath] = get_processed_revisions_files(
        project_name=project_name,
        report_type=DFBR,
        file_name_filter=fnf,
        only_newest=False
    )

    failed_report_files: tp.List[ReportFilepath] = get_failed_revisions_files(
        project_name=project_name,
        report_type=DFBR,
        file_name_filter=fnf,
        only_newest=False
    )

    return report_files, failed_report_files


def get_both_reports_for_case_study(
    case_study: CaseStudy
) -> tp.Tuple[tp.List[SFBR], tp.List[DFBR]]:
    structural_report_files, structural_failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    dataflow_report_files, dataflow_failed_report_files = get_dataflow_report_files_for_project(
        case_study.project_name
    )

    SFBRs: tp.List[SFBR] = [
        load_structural_feature_blame_report(SRFP)
        for SRFP in structural_report_files
    ]
    DFBRs: tp.List[DFBR] = [
        load_dataflow_feature_blame_report(DRFP)
        for DRFP in dataflow_report_files
    ]
    return (SFBRs, DFBRs)


def get_commit_dataflow_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:

    number_active_commits = num_active_commits(
        repo_folder=get_local_project_git_path(case_study.project_name)
    )
    SFBRs, DFBRs = get_both_reports_for_case_study(case_study)
    data_frame = generate_commit_dcfi_data(SFBRs, DFBRs, number_active_commits)

    return data_frame


class FeatureInwardDataflowPlot(Plot, plot_name="feature_inward_dataflow_plot"):

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = pd.concat([
            get_commit_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ])
        data = data.loc[data['part_of_feature'] == 0]
        # data = data.loc[data['num_interacting_features'] > 0]
        plt = sns.histplot(
            data=data,
            x='num_interacting_features',
            #kde=True,
            binwidth=1,
        )

        plt.set(
            xlabel="Number Interacting Features",
            ylabel="Commit Count",
            title='Dataflow from outside into features'
            ' - projects: ' +
            ",".join(case_study.project_name for case_study in case_studies)
        )


class FeatureInwardDataflowPlotGenerator(
    PlotGenerator,
    generator_name="feature-inward-dataflow-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureInwardDataflowPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureExistingInwardDataflowPlot(
    Plot, plot_name="feature_existing_inward_dataflow_plot"
):

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = pd.concat([
            get_commit_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ])
        data = data.loc[data['part_of_feature'] == 0]
        data = data.loc[data['num_interacting_features'] > 0]
        plt = sns.histplot(
            data=data,
            x='num_interacting_features',
            #kde=True,
            binwidth=1,
        )

        plt.set(
            xlabel="Number Interacting Features",
            ylabel="Commit Count",
            title='Dataflow from outside of features'
            ' - projects: ' +
            ",".join(case_study.project_name for case_study in case_studies)
        )


class FeatureExistingInwardDataflowPlotGenerator(
    PlotGenerator,
    generator_name="feature-existing-inward-dataflow-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureExistingInwardDataflowPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


def get_feature_dataflow_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:

    SFBRs, DFBRs = get_both_reports_for_case_study(case_study)
    data_frame = generate_feature_dcfi_data(SFBRs, DFBRs)

    return data_frame


class FeatureSizeCorrDFBRPlot(Plot, plot_name="feature_size_corr_dfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        data = pd.concat([
            get_feature_dataflow_data_for_case_study(case_study)
            for case_study in case_studies
        ])
        print(data)
        plt = sns.regplot(
            data=data, x='feature_size', y='num_interacting_commits_outside'
        )


class FeatureSizeCorrDFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-size-corr-dfbr-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        return [
            FeatureSizeCorrDFBRPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


########## Author ###########


def get_feature_author_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:
    report_files, failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    repo_path = get_local_project_git_path(case_study.project_name)
    report = load_structural_feature_blame_report(report_files[0])
    data_frame: pd.DataFrame = generate_feature_author_scfi_data(
        report, repo_path
    )

    return data_frame


def get_stacked_author_data_for_case_studies(
    case_studies: tp.List[CaseStudy]
) -> pd.DataFrame:
    rows = []
    projects_data = [
        get_feature_author_data_for_case_study(case_study
                                              ).loc[:,
                                                    "num_implementing_authors"]
        for case_study in case_studies
    ]
    max_num_implementing_authors = max([
        max(project_data) for project_data in projects_data
    ])

    for case_study, project_data in zip(case_studies, projects_data):
        count: [int] = [0 for i in range(0, max_num_implementing_authors)]
        for num_implementing_authors in project_data:
            count[num_implementing_authors -
                  1] = count[num_implementing_authors - 1] + 1

        rows.append([case_study.project_name] + count)

    return pd.DataFrame(
        rows,
        columns=['Project', '1 Author'] + [
            str(i) + ' Authors'
            for i in range(2, max_num_implementing_authors + 1)
        ]
    )


class FeatureAuthorDisSCFIPlot(Plot, plot_name="feature_author_dis_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]

        data = get_stacked_author_data_for_case_studies(case_studies)

        data.set_index('Project').plot(kind='bar', stacked=True)


class FeatureAuthorDisSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-author-dis-scfi-plot",
    options=[REQUIRE_MULTI_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            FeatureAuthorDisSCFIPlot(
                self.plot_config, case_studies=case_studies, **self.plot_kwargs
            )
        ]


class FeatureAuthorCorrSCFIPlot(
    Plot, plot_name="feature_author_corr_scfi_plot"
):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        data = get_feature_author_data_for_case_study(case_study)
        print(data)
        ax = sns.regplot(
            data=data, x='feature_size', y='num_implementing_authors'
        )


class FeatureAuthorCorrSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-author-corr-scfi-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureAuthorCorrSCFIPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]

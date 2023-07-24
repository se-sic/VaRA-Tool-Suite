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
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.git_util import num_commits


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
    for RFP in report_files:
        report = load_structural_feature_blame_report(RFP)
        if data_frame.empty:
            data_frame = generate_feature_scfi_data(report)
        else:
            data_frame = pd.concat([
                data_frame, generate_feature_scfi_data(report)
            ])
    return data_frame


def get_structural_commit_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:
    report_files, failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    data_frame: pd.DataFrame = pd.DataFrame()
    for RFP in report_files:
        report = load_structural_feature_blame_report(RFP)
        if data_frame.empty:
            data_frame = generate_commit_scfi_data(report)
        else:
            data_frame = pd.concat([
                data_frame, generate_commit_scfi_data(report)
            ])
    print(data_frame)
    return data_frame


class FeatureScopeCorrSFBRPlot(Plot, plot_name="feature_scope_corr_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_feature_data_for_case_study(case_study)

        data = df.sort_values(by=['feature_scope'])
        sns.regplot(data=data, x='feature_scope', y='num_interacting_commits')


class FeatureScopeCorrSFBRPlotGenerator(
    PlotGenerator,
    generator_name="feature-scope-corr-sfbr-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureScopeCorrSFBRPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


class FeatureDisSFBRPlot(Plot, plot_name="feature_dis_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_feature_data_for_case_study(case_study)

        sns.displot(data=df, x='num_interacting_commits', kde=True)


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


class CommitDisSFBRPlot(Plot, plot_name="commit_dis_sfbr_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_commit_data_for_case_study(case_study)

        sns.displot(data=df, x='num_interacting_features', kde=True)


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


def get_dataflow_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
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
    number_commits = num_commits(
        c_start=case_study.revisions[0],
        repo_folder="/scratch/s8sisteu/VARA_ROOT/benchbuild/tmp/" +
        case_study.project_name
    )
    data_frame = generate_commit_dcfi_data(SFBRs, DFBRs, number_commits)

    return data_frame


class FeatureDCFIPlot(Plot, plot_name="feature_dcfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        data = get_dataflow_data_for_case_study(case_study)
        ax = sns.displot(
            data=data,
            x='num_interacting_features',
            hue='part_of_feature',
            kde=True
        )


class FeatureDCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-dcfi-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureDCFIPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


########## Author ###########


def get_feature_author_data_for_case_study(
    case_study: CaseStudy
) -> pd.DataFrame:
    report_files, failed_report_files = get_structural_report_files_for_project(
        case_study.project_name
    )
    data_frame: pd.DataFrame = pd.DataFrame()
    for RFP in report_files:
        report = load_structural_feature_blame_report(RFP)
        if data_frame.empty:
            data_frame = generate_feature_author_scfi_data(report)
        else:
            data_frame = pd.concat([
                data_frame, generate_feature_author_scfi_data(report)
            ])
    print(data_frame)
    return data_frame


class FeatureAuthorDisSCFIPlot(Plot, plot_name="feature_author_dis_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        data = get_feature_author_data_for_case_study(case_study)
        ax = sns.displot(
            data=data,
            x='num_implementing_authors',
            kde=True
        )


class FeatureAuthorDisSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-author-dis-scfi-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureAuthorDisSCFIPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]
    

class FeatureAuthorCorrSCFIPlot(Plot, plot_name="feature_author_corr_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        data = get_feature_author_data_for_case_study(case_study)
        ax = sns.regplot(
            data=data,
            x='feature_scope', 
            y='num_implementing_authors'
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
import typing as tp

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
import seaborn as sns
from matplotlib import axes

from varats.data.reports.feature_blame_report import (
    StructuralFeatureBlameReport as SFBR,
)
from varats.data.reports.feature_blame_report import (
    DataflowFeatureBlameReport as DFBR,
)
from varats.data.reports.feature_blame_report import (
    generate_features_scfi_data,
    generate_commit_dcfi_data,
)
from varats.jupyterhelper.file import (
    load_structural_feature_blame_report,
    load_dataflow_feature_blame_report,
)
from varats.mapping.commit_map import CommitMap, get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plot_utils import align_yaxis, pad_axes, annotate_correlation
from varats.plot.plots import PlotGenerator
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
)
from varats.ts_utils.click_param_types import REQUIRE_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import ShortCommitHash, num_commits


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


def get_structural_data_for_case_study(case_study: CaseStudy) -> pd.DataFrame:
    report_files, failed_report_files = get_report_files_for_project(
        case_study.project_name, type(SFBR)
    )
    data_frame: pd.DataFrame = pd.DataFrame()
    for RFP in report_files:
        report = load_structural_feature_blame_report(RFP)
        if data_frame.empty:
            data_frame = generate_features_scfi_data(report)
        else:
            data_frame = pd.concat([
                data_frame, generate_features_scfi_data(report)
            ])

    return data_frame


class FeatureSCFIPlot(Plot, plot_name="feature_scfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]

        df = get_structural_data_for_case_study(case_study)

        data = df.sort_values(by=['feature_scope'])
        sns.regplot(data=data, x='feature_scope', y='num_interacting_commits')


class FeatureSCFIPlotGenerator(
    PlotGenerator,
    generator_name="feature-scfi-plot",
    options=[REQUIRE_CASE_STUDY]
):

    def generate(self) -> tp.List[Plot]:
        case_study: CaseStudy = self.plot_kwargs.pop("case_study")
        return [
            FeatureSCFIPlot(
                self.plot_config, case_study=case_study, **self.plot_kwargs
            )
        ]


######## DATAFLOW #########


def get_dataflow_data_for_case_study(
    case_study: CaseStudy
) -> tp.Tuple[pd.DataFrame, pd.DataFrame]:
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
    data_frame_1, data_frame_2 = generate_commit_dcfi_data(
        SFBRs, DFBRs, number_commits
    )

    return data_frame_1, data_frame_2


class FeatureDCFIPlot(Plot, plot_name="feature_dcfi_plot"):

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        df_1, df_2 = get_dataflow_data_for_case_study(case_study)
        data_1 = df_1.sample(frac=1)
        ax = sns.scatterplot(
            data=data_1,
            x='num_interacting_features',
            y='commits',
            label='commits_in_features'
        )
        data_2 = df_2.sample(frac=1)
        ax = sns.scatterplot(
            data=data_2,
            x='num_interacting_features',
            y='commits',
            label='commits_not_in_features'
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

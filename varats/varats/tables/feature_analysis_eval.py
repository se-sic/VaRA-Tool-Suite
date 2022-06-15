"""Module for PhASAR feature taint analysis evaluation tables."""
import logging
import re
import typing as tp
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisGroundTruth,
    FeatureAnalysisReport,
    FeatureAnalysisReportEval,
)
from varats.jupyterhelper.file import load_feature_analysis_report
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import ProjectBinaryWrapper
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table, wrap_table_in_document
from varats.table.tables import TableFormat

LOG = logging.Logger(__name__)


def filter_report_paths_binary(
    report_files: tp.List[Path], binary: ProjectBinaryWrapper
) -> tp.List[Path]:
    return list(
        filter(
            lambda x: ReportFilename(x).binary_name == binary.name, report_files
        )
    )


def filter_ground_truth_paths_binary(
    gt_files: tp.List[Path], binary: ProjectBinaryWrapper
) -> tp.List[Path]:
    return list(filter(lambda x: binary.name in x, gt_files))


class PhasarFeatureAnalysisProjectEvalTable(Table):
    """
    Evaluates gathered PhASAR feature analysis data through camparision with a
    given ground truth for a single revision of a single project.

    In case multiple binaries are given, make sure that the features to be part
    of the table are part of the ground truth file of each binary.
    """

    NAME = "phasar_fta_eval_project"

    def __init__(self, **kwargs: tp.Any):
        super().__init__(self.NAME, **kwargs)

    def tabulate(self) -> str:
        paper_config = get_loaded_paper_config()
        case_studies: tp.List[CaseStudy] = sorted(
            paper_config.get_all_case_studies(), key=lambda x: x.project_name
        )

        if len(case_studies) == 0:
            LOG.debug(f"paper_config={paper_config.path}")
            raise LookupError(
                "No case study found in the current paper config!"
            )

        case_study = case_studies[0]
        if len(case_studies) > 1:
            if self.table_kwargs['table_case_study'] is not None:
                case_study = self.table_kwargs['table_case_study']
            elif 'project' in self.table_kwargs:
                case_studies_prj: tp.List[CaseStudy
                                         ] = paper_config.get_case_studies(
                                             self.table_kwargs['project']
                                         )
                if len(case_studies_prj) > 1:
                    self.__log_warning()
                case_study = case_studies_prj[0]
            else:
                self.__log_warning()

        report_files = get_processed_revisions_files(
            case_study.project_name, FeatureAnalysisReport,
            get_case_study_file_name_filter(case_study)
        )
        if len(report_files) == 0:
            raise AssertionError(
                f"No FeatureAnalysisReport found for project {case_study.project_name}"
            )

        cs_revisions = case_study.revisions
        if len(cs_revisions) > 1:
            LOG.debug(f"revisions={cs_revisions}")
            self.__log_warning()

        if 'ground_truth' not in self.table_kwargs:
            raise AssertionError(
                "No ground truth file found!\n"
                "vara-table [OPTIONS] phasar_fta_eval_project ground_truth=PATH[,PATH,...]"
            )
        gt_files = re.compile(r',\s*').split(self.table_kwargs['ground_truth'])

        features: tp.List[str] = []
        if 'features' in self.table_kwargs:
            features = re.compile(r',\s*').split(self.table_kwargs['features'])

        insts: int = 0
        data: tp.List[pd.DataFrame] = []
        binaries = case_study.project_cls.binaries_for_revision(cs_revisions[0])
        for binary in binaries:
            name = ""
            if len(binaries) > 1:
                name = binary.name

            # report
            report_files_for_binary = filter_report_paths_binary(
                report_files, binary
            )
            report: tp.Optional[FeatureAnalysisReport] = None
            if not report_files_for_binary:
                LOG.warning(f"No report file given for binary {name}!")
                continue
            report = load_feature_analysis_report(report_files_for_binary[0])

            # ground truth
            gt_files_for_binary = filter_ground_truth_paths_binary(
                gt_files, binary
            )
            ground_truth: tp.Optional[FeatureAnalysisGroundTruth]
            if not gt_files_for_binary:
                LOG.warning(f"No ground truth file given for binary {name}!")
                continue
            ground_truth = FeatureAnalysisGroundTruth(gt_files_for_binary[0])

            if features == []:
                features = ground_truth.get_features()
            features = sorted(features)

            eval: FeatureAnalysisReportEval = FeatureAnalysisReportEval(
                report, ground_truth, features.copy()
            )

            data.append(self.__create_eval_df(eval, ['Total'] + features, name))

            insts += report.meta_data.num_br_switch_insts

        df = pd.concat(data)

        if self.format in [
            TableFormat.LATEX, TableFormat.LATEX_BOOKTABS, TableFormat.LATEX_RAW
        ]:
            col_format = 'ccc' if len(binaries) > 1 else 'cc'
            col_format += '|cc' + '|cc' * len(features)
            caption = (
                f"Evaluation of project {case_study.project_name}. "
                f"In total there were {insts} br and switch instructions."
            )
            table = df.to_latex(
                column_format=col_format,
                longtable=True,
                multicolumn=True,
                multicolumn_format='c',
                multirow=True,
                caption=caption,
                position='t'
            )
            return str(table) if table else ""

        return tabulate(df, df.columns, self.format
                       ) + "\n\nbr/switch Instructions: " + str(insts)

    def __create_eval_df(
        self, eval: FeatureAnalysisReportEval, entries: tp.List[str],
        binary: str
    ) -> pd.DataFrame:
        data: tp.List[pd.DataFrame] = []
        for entry in entries:
            true_pos = eval.get_true_pos(entry)
            false_pos = eval.get_false_pos(entry)
            false_neg = eval.get_false_neg(entry)
            true_neg = eval.get_true_neg(entry)

            if binary:
                data.append(
                    pd.DataFrame([[true_pos, false_pos], [false_neg, true_neg]],
                                 index=pd.MultiIndex.from_product([[
                                     'Analysis Results'
                                 ], [binary.name], ['Pos', 'Neg']]),
                                 columns=pd.MultiIndex.from_product([[
                                     'Ground Truth'
                                 ], [entry], ['Pos', 'Neg']]))
                )
            else:
                data.append(
                    pd.DataFrame([[true_pos, false_pos], [false_neg, true_neg]],
                                 index=pd.MultiIndex.from_product([[
                                     'Analysis Results'
                                 ], ['Pos', 'Neg']]),
                                 columns=pd.MultiIndex.from_product([[
                                     'Ground Truth'
                                 ], [entry], ['Pos', 'Neg']]))
                )

        return pd.concat(data, axis=1)

    def __log_warning(self) -> None:
        LOG.warning(
            "This table is only designed for usage with a single revision of one project "
            "but more were found.\nAll case studies and revisions except for the "
            "first one are ignored.\n"
            "To specify a project of the current paper config use --project=PROJECT.\n"
            "To specify a case study of the current paper config use --cs-path=PATH.\n"
        )

    def wrap_table(self, table: str) -> str:
        return wrap_table_in_document(table=table, landscape=True)

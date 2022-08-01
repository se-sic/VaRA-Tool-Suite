"""Module for PhASAR feature taint analysis evaluation tables."""
import logging
import re
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisGroundTruth,
    FeatureAnalysisReport,
    FeatureAnalysisReportEval,
)
from varats.jupyterhelper.file import load_feature_analysis_report
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import ProjectBinaryWrapper
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_CASE_STUDY,
    REQUIRE_MULTI_CASE_STUDY,
)

LOG = logging.Logger(__name__)

REQUIRE_GROUND_TRUTH: CLIOptionTy = make_cli_option(
    "-gt",
    "--ground-truth",
    type=str,
    required=True,
    metavar="PATHS",
    help="One or more ground truths to use."
)

OPTIONAL_FEATURES: CLIOptionTy = make_cli_option(
    "--features",
    type=str,
    required=False,
    metavar="FEATURES",
    help="The features to use explicitly."
)


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
    return list(filter(lambda x: binary.name in str(x), gt_files))


class PhasarFeatureAnalysisProjectEvalTable(
    Table, table_name="fta_project_eval_table"
):
    """
    Evaluates gathered PhASAR feature analysis data through camparision with a
    given ground truth for a single revision of a single project. Includes
    feature-specific evaluation information.

    In case multiple binaries are given, make sure that the features to be part
    of the table are part of the ground truth file of each binary.
    """

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs['case_study']

        report_files = get_processed_revisions_files(
            case_study.project_name, FeatureAnalysisReport,
            get_case_study_file_name_filter(case_study)
        )
        if len(report_files) == 0:
            raise AssertionError(
                "No FeatureAnalysisReport found for case study "
                f"{case_study.project_name}"
            )

        cs_revisions = case_study.revisions
        if len(cs_revisions) > 1:
            LOG.debug(f"revisions={cs_revisions}")
            LOG.warning(
                "This tabled is only designed for usage with one revision "
                "but more were found. All revisions expect for the first "
                "one are ignored."
            )

        gt_files: tp.List[Path] = [
            Path(gt) for gt in \
                re.compile(r',\s*').split(self.table_kwargs['ground_truth'])
        ]

        features: tp.List[str] = []
        if self.table_kwargs['features'] is not None:
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
                LOG.warning(f"No report file given for binary {binary.name}!")
                continue
            report = load_feature_analysis_report(report_files_for_binary[0])

            # ground truth
            gt_files_for_binary = filter_ground_truth_paths_binary(
                gt_files, binary
            )
            ground_truth: tp.Optional[FeatureAnalysisGroundTruth]
            if not gt_files_for_binary:
                LOG.warning(
                    f"No ground truth file given for binary {binary.name}!"
                )
                continue
            ground_truth = FeatureAnalysisGroundTruth(gt_files_for_binary[0])

            # features
            if features == []:
                features = ground_truth.get_features()
            features = sorted(features)

            evaluation: FeatureAnalysisReportEval = FeatureAnalysisReportEval(
                report, ground_truth, features.copy()
            )

            data.append(
                self.__create_eval_df(evaluation, ['Total'] + features, name)
            )

            insts += report.meta_data.num_br_switch_insts

        df = pd.concat(data)

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = (
                'ccc|cc' +
                '|cc' * len(features) if len(binaries) > 1 else 'cc|cc' +
                '|cc' * len(features)
            )
            kwargs["multicol_align"] = "c"
            kwargs["caption"] = (
                f"Evaluation of project {case_study.project_name}. "
                f"In total there were {insts} br and switch instructions."
            )
            kwargs['position'] = 't'

        return dataframe_to_table(
            df,
            table_format,
            wrap_table=wrap_table,
            wrap_landscape=True,
            **kwargs
        )

    def __create_eval_df(
        self, evaluation: FeatureAnalysisReportEval, entries: tp.List[str],
        binary: str
    ) -> pd.DataFrame:
        data: tp.List[pd.DataFrame] = []
        for entry in entries:
            true_pos = evaluation.get_true_pos(entry)
            false_pos = evaluation.get_false_pos(entry)
            false_neg = evaluation.get_false_neg(entry)
            true_neg = evaluation.get_true_neg(entry)

            if binary:
                data.append(
                    pd.DataFrame([[true_pos, false_pos], [false_neg, true_neg]],
                                 index=pd.MultiIndex.from_product([[
                                     'Analysis Results'
                                 ], [binary], ['Pos', 'Neg']]),
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


class PhasarFeatureAnalysisProjectEvalTableGenerator(
    TableGenerator,
    generator_name="fta-project-eval-table",
    options=[REQUIRE_CASE_STUDY, REQUIRE_GROUND_TRUTH, OPTIONAL_FEATURES]
):
    """Generates a fta-project-eval table for the selected case study."""

    def generate(self) -> tp.List[Table]:
        return [
            PhasarFeatureAnalysisProjectEvalTable(
                self.table_config, **self.table_kwargs
            )
        ]


class PhasarFeatureAnalysisTotalEvalTable(
    Table, table_name="fta_total_eval_table"
):
    """Evaluates gathered PhASAR feature analysis data through camparision with
    a given ground truth for a single revision."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        cs_data: tp.List[pd.DataFrame] = []
        col_format = 'cc'

        gt_files: tp.List[Path] = [
            Path(gt) for gt in \
                re.compile(r',\s*').split(self.table_kwargs['ground_truth'])
        ]

        for case_study in sorted(
            tp.cast(tp.List[CaseStudy], self.table_kwargs["case_study"]),
            key=lambda x: x.project_name
        ):
            report_files = get_processed_revisions_files(
                case_study.project_name, FeatureAnalysisReport,
                get_case_study_file_name_filter(case_study)
            )
            if len(report_files) == 0:
                raise AssertionError(
                    "No FeatureAnalysisReport found for case study "
                    f"{case_study.project_name}"
                )

            cs_revisions = case_study.revisions
            if len(cs_revisions) > 1:
                LOG.debug(f"revisions={cs_revisions}")
                LOG.warning(
                    "This tabled is only designed for usage with one revision "
                    "but more were found. All revisions expect for the first "
                    "one are ignored."
                )

            binaries = case_study.project_cls.binaries_for_revision(
                cs_revisions[0]
            )
            for binary in binaries:
                if len(binaries) > 1:
                    name = case_study.project_name + "-" + binary.name
                else:
                    name = case_study.project_name

                # report
                report_files_for_binary = filter_report_paths_binary(
                    report_files, binary
                )
                report: tp.Optional[FeatureAnalysisReport] = None
                if not report_files_for_binary:
                    LOG.warning(f"No report file given for binary {name}!")
                    continue
                report = load_feature_analysis_report(
                    report_files_for_binary[0]
                )

                # ground truth
                gt_files_for_binary = filter_ground_truth_paths_binary(
                    gt_files, binary
                )
                ground_truth: tp.Optional[FeatureAnalysisGroundTruth]
                if not gt_files_for_binary:
                    LOG.warning(
                        f"No ground truth file given for binary {name}!"
                    )
                    continue
                ground_truth = FeatureAnalysisGroundTruth(
                    gt_files_for_binary[0]
                )

                evaluation: FeatureAnalysisReportEval = (
                    FeatureAnalysisReportEval(report, ground_truth, [])
                )

                cs_data.append(self.__create_eval_df(evaluation, name))

                col_format += '|cc'

        df = pd.concat(cs_data, axis=1)

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = col_format
            kwargs["multicol_align"] = "c"
            kwargs['position'] = 't'

        return dataframe_to_table(
            df,
            table_format,
            wrap_tale=wrap_table,
            wrap_landscape=True,
            **kwargs
        )

    def __create_eval_df(
        self, evaluation: FeatureAnalysisReportEval, entry: str
    ) -> pd.DataFrame:
        true_pos = evaluation.get_true_pos()
        false_pos = evaluation.get_false_pos()
        false_neg = evaluation.get_false_neg()
        true_neg = evaluation.get_true_neg()

        df = pd.DataFrame([[true_pos, false_pos], [false_neg, true_neg]],
                          index=pd.MultiIndex.from_product([[
                              'Analysis Results'
                          ], ['Pos', 'Neg']]),
                          columns=pd.MultiIndex.from_product([['Ground Truth'],
                                                              [entry],
                                                              ['Pos', 'Neg']]))
        return df


class PhasarFeatureAnalysisTotalEvalTableGenerator(
    TableGenerator,
    generator_name="fta-total-eval-table",
    options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_GROUND_TRUTH]
):
    """Generates a fta-total-eval table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            PhasarFeatureAnalysisTotalEvalTable(
                self.table_config, **self.table_kwargs
            )
        ]

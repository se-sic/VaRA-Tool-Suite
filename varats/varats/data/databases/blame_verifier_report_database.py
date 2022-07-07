"""Module for the BlameVerifierReportDatabase class."""
import re
import typing as tp
from enum import Enum
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOptTBAA,
    BlameVerifierReportOpt,
)
from varats.jupyterhelper.file import (
    load_blame_verifier_report_no_opt_tbaa,
    load_blame_verifier_report_opt,
)
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilename
from varats.revision.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)


class OptLevel(Enum):
    """Enum for the different optimization levels used to create the verifier
    report."""
    value: int  # pylint: disable=invalid-name

    NO_OPT = 0
    OPT = 2


class BlameVerifierReportDatabase(
    EvaluationDatabase,
    column_types={
        "opt_level": 'int64',
        "total": 'int64',
        "successful": 'int64',
        "failed": 'int64',
        "undetermined": 'int64'
    },
    cache_id="blame_verifier_report_data"
):
    """Provides access to blame verifier report data."""

    report_file_name_pattern = re.compile(r"[^/]+$")

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        # pylint: disable=unused-argument

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:

            report_file_name_match = re.search(
                BlameVerifierReportDatabase.report_file_name_pattern,
                str(report_path)
            )

            if report_file_name_match:
                report_file_name = report_file_name_match.group()
            else:
                raise RuntimeWarning(
                    "report file name could not be read from report path"
                )

            report: tp.Union[BlameVerifierReportOpt,
                             BlameVerifierReportNoOptTBAA]

            if BlameVerifierReportOpt.is_correct_report_type(report_file_name):
                report_opt = load_blame_verifier_report_opt(report_path)
                report = report_opt
                opt_level = OptLevel.OPT.value

            elif BlameVerifierReportNoOptTBAA.is_correct_report_type(
                report_file_name
            ):
                report_no_opt = load_blame_verifier_report_no_opt_tbaa(
                    report_path
                )

                report = report_no_opt
                opt_level = OptLevel.NO_OPT.value

            else:
                raise RuntimeWarning("unknown report type")

            number_of_total_annotations = report.get_total_annotations()
            number_of_successful_annotations = \
                report.get_successful_annotations()
            number_of_failed_annotations = report.get_failed_annotations()
            number_of_undetermined_annotations \
                = report.get_undetermined_annotations()

            return pd.DataFrame(
                {
                    'revision': report.head_commit.hash,
                    'time_id': commit_map.short_time_id(report.head_commit),
                    'opt_level': opt_level,
                    'total': number_of_total_annotations,
                    'successful': number_of_successful_annotations,
                    'failed': number_of_failed_annotations,
                    'undetermined': number_of_undetermined_annotations
                },
                index=[0]
                # Add prefix of report name to head_commit to differentiate
                # between reports with and without optimization
            ), report.head_commit.hash + report_path.name.split("-", 1)[0], str(
                report_path.stat().st_mtime_ns
            )

        report_files_opt = get_processed_revisions_files(
            project_name, BlameVerifierReportOpt,
            get_case_study_file_name_filter(case_study)
        )

        report_files_no_opt = get_processed_revisions_files(
            project_name, BlameVerifierReportNoOptTBAA,
            get_case_study_file_name_filter(case_study)
        )

        report_files = report_files_opt + report_files_no_opt

        failed_report_files_opt = get_failed_revisions_files(
            project_name, BlameVerifierReportOpt,
            get_case_study_file_name_filter(case_study)
        )

        failed_report_files_no_opt = get_failed_revisions_files(
            project_name, BlameVerifierReportNoOptTBAA,
            get_case_study_file_name_filter(case_study)
        )

        failed_report_files = \
            failed_report_files_opt + failed_report_files_no_opt

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report, lambda path:
            ReportFilename(path).commit_hash.hash + path.name.split("-", 1)[0],
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )
        return data_frame

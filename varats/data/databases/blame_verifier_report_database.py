"""Module for the BlameVerifierReportDatabase class."""
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportNoOpt,
    BlameVerifierReportOpt,
)
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.jupyterhelper.file import (
    load_blame_verifier_report_no_opt,
    load_blame_verifier_report_opt,
)
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter


class BlameVerifierReportDatabase(
    EvaluationDatabase,
    columns=["opt_level", "total", "successes", "failures", "undetermined"],
    cache_id="blame_verifier_report_data"
):
    """Provides access to blame verifier report data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:

        # Decide in nested methods what the loaded report type is
        bvr_type = MetaReport

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.opt_level = df_layout.opt_level.astype('int64')
            df_layout.total = df_layout.total.astype('int64')
            df_layout.successes = df_layout.successes.astype('int64')
            df_layout.failures = df_layout.failures.astype('int64')
            df_layout.undetermined = df_layout.undetermined.astype('int64')
            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            nonlocal bvr_type

            report_opt = load_blame_verifier_report_opt(report_path)
            report_no_opt = load_blame_verifier_report_no_opt(report_path)

            if report_opt is not None:
                report = report_opt
                bvr_type = BlameVerifierReportOpt
                opt_level = 2
            elif report_no_opt is not None:
                report = report_no_opt
                bvr_type = BlameVerifierReportNoOpt
                opt_level = 0
            else:
                raise RuntimeWarning("loaded unknown report type")

            number_of_total_annotations = report.get_total_annotations()
            number_of_successful_annotations = \
                report.get_successful_annotations()
            number_of_failed_annotations = report.get_failed_annotations()
            number_of_undetermined_annotations \
                = report.get_undetermined_annotations()

            return pd.DataFrame({
                'revision': report.head_commit,
                'opt_level': opt_level,
                'total': number_of_total_annotations,
                'successful': number_of_successful_annotations,
                'failed': number_of_failed_annotations,
                'undetermined': number_of_undetermined_annotations
            },
                                index=[0]), report.head_commit, str(
                                    report_path.stat().st_mtime_ns
                                )

        report_files = get_processed_revisions_files(
            project_name, bvr_type, get_case_study_file_name_filter(case_study)
        )

        failed_report_files = get_failed_revisions_files(
            project_name, bvr_type, get_case_study_file_name_filter(case_study)
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report,
            lambda path: MetaReport.get_commit_hash_from_result_file(path.name),
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )
        return data_frame

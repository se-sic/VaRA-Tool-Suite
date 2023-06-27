"""Module for feature blame-data metrics."""
import typing as tp
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.feature_blame_report import (
    StructuralFeatureBlameReport,
    DataflowFeatureBlameReport,
    generate_features_scfi_data
)
from varats.experiments.vara.feature_blame_report_experiment import (
    StructuralFeatureBlameReportExperiment,
    DataflowFeatureBlameReportExperiment
)
from varats.jupyterhelper.file import (
    load_structural_feature_blame_report,
    load_dataflow_feature_blame_report
)
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import get_local_project_git
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
    get_processed_revisions,
)
from varats.data.databases.blame_diff_metrics_database import (
    get_predecessor_report_file,
    get_successor_report_file,
    id_from_paths,
    timestamp_from_paths,
    compare_timestamps
)
from varats.utils.git_util import (
    ChurnConfig,
    calc_code_churn,
    create_commit_lookup_helper,
    ShortCommitHash,
    FullCommitHash,
)

def build_structural_report_files_tuple(
    project_name: str, case_study: tp.Optional[CaseStudy]
) -> tp.Tuple[tp.Dict[ShortCommitHash, ReportFilepath], tp.Dict[
    ShortCommitHash, ReportFilepath]]:
    """
    Build the mappings between commit hash to its corresponding report file
    path, where the first mapping corresponds to commit hashes and their
    successful report files and the second mapping to commit hashes and their
    failed report files.

    Args:
        project_name: the name of the project
        case_study: the selected CaseStudy

    Returns:
        the mappings from commit hash to successful and failed report files as
        tuple
    """
    report_files: tp.Dict[ShortCommitHash, ReportFilepath] = {
        report.report_filename.commit_hash: report
        for report in get_processed_revisions_files(
            project_name,
            StructuralFeatureBlameReportExperiment,
            file_name_filter=get_case_study_file_name_filter(case_study)
            if case_study else lambda x: False,
        )
    }

    failed_report_files: tp.Dict[ShortCommitHash, ReportFilepath] = {
        report.report_filename.commit_hash: report
        for report in get_failed_revisions_files(
            project_name,
            StructuralFeatureBlameReportExperiment,
            file_name_filter=get_case_study_file_name_filter(case_study)
            if case_study else lambda x: False,
        )
    }
    return report_files, failed_report_files

ReportPairTupleList = tp.List[tp.Tuple[ReportFilepath, ReportFilepath]]

def build_structural_report_pairs_tuple(
    project_name: str, commit_map: CommitMap, case_study: tp.Optional[CaseStudy]
) -> tp.Tuple[ReportPairTupleList, ReportPairTupleList]:
    """
    Builds a tuple of tuples (ReportPairTupleList, ReportPairTupleList) of
    successful report files with their corresponding predecessors and tuples of
    failed report files with their corresponding predecessor.

    Args:
        project_name: the name of the project
        commit_map: the selected CommitMap
        case_study: the selected CaseStudy

    Returns:
        the tuple of report file to predecessor tuples for all successful and
        failed reports
    """

    report_files, failed_report_files = build_structural_report_files_tuple(
        project_name, case_study
    )

    sampled_revs: tp.List[ShortCommitHash]
    if case_study:
        sampled_revs = [
            rev.to_short_commit_hash() for rev in case_study.revisions
        ]
    else:
        sampled_revs = get_processed_revisions(
            project_name, StructuralFeatureBlameReportExperiment
        )
    short_time_id_cache: tp.Dict[ShortCommitHash, int] = {
        rev: commit_map.short_time_id(rev) for rev in sampled_revs
    }

    report_pairs: tp.List[tp.Tuple[ReportFilepath, ReportFilepath]] = [
        (report, pred) for report, pred in [(
            report_file,
            get_predecessor_report_file(
                c_hash, commit_map, short_time_id_cache, report_files,
                sampled_revs
            )
        ) for c_hash, report_file in report_files.items()] if pred is not None
    ]

    failed_report_pairs: tp.List[tp.Tuple[ReportFilepath, ReportFilepath]] = [
        (report, pred) for report, pred in chain.from_iterable(
            [[(
                report_file,
                get_predecessor_report_file(
                    c_hash, commit_map, short_time_id_cache, report_files,
                    sampled_revs
                )
            ),
              (
                  get_successor_report_file(
                      c_hash, commit_map, short_time_id_cache, report_files,
                      sampled_revs
                  ), report_file
              )] for c_hash, report_file in failed_report_files.items()]
        ) if report is not None and pred is not None
    ]
    return report_pairs, failed_report_pairs

class FeaturesSCFIMetricsDatabase(
    EvaluationDatabase,
    cache_id="features_SCFI_metrics_database",
    column_types={"feature": 'str', "num_interacting_commits": 'int64', "feature_scope": 'int64'}
):
    """Metrics database that contains all structural cfi information of every feature
    based on a `StructuralFeatureBlameReport`."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        
        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout
        
        def create_data_frame_for_report(
            report_path: ReportFilepath
        ) -> pd.DataFrame:
            report = load_structural_feature_blame_report(report_path)
            return generate_features_scfi_data(report)
        
        report_pairs, failed_report_pairs = build_structural_report_pairs_tuple(
            project_name, commit_map, case_study
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_pairs, failed_report_pairs,
            create_dataframe_layout, create_data_frame_for_report,
            id_from_paths, timestamp_from_paths, compare_timestamps
        )

        return data_frame
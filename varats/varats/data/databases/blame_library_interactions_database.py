"""Module for the BlameLibraryInteractionsDatabase class."""
import typing as tp
from pathlib import Path

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_report import (
    BlameReport,
    gen_base_to_inter_commit_repo_pair_mapping,
)
from varats.jupyterhelper.file import load_blame_report
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilename
from varats.revision.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.utils.git_util import FullCommitHash


class BlameLibraryInteractionsDatabase(
    EvaluationDatabase,
    cache_id="blame_library_interaction_data",
    column_types={
        "base_hash": 'str',
        "base_lib": 'str',
        "inter_hash": 'str',
        "inter_lib": 'str',
        "amount": 'int'
    }
):
    """Provides access to blame library interaction data."""

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
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_blame_report(report_path)
            base_inter_c_repo_pair_mapping = \
                gen_base_to_inter_commit_repo_pair_mapping(report)

            def build_dataframe_row(
                base_hash: FullCommitHash, base_library: str,
                inter_hash: FullCommitHash, inter_library: str, amount: int
            ) -> tp.Dict[str, tp.Any]:

                data_dict: tp.Dict[str, tp.Any] = {
                    'revision': report.head_commit.hash,
                    'time_id': commit_map.short_time_id(report.head_commit),
                    'base_hash': base_hash.hash,
                    'base_lib': base_library,
                    'inter_hash': inter_hash.hash,
                    'inter_lib': inter_library,
                    'amount': amount
                }
                return data_dict

            result_data_dicts: tp.List[tp.Dict[str, tp.Any]] = []

            for base_pair in base_inter_c_repo_pair_mapping:
                inter_pair_amount_dict = base_inter_c_repo_pair_mapping[
                    base_pair]

                for inter_pair in inter_pair_amount_dict:
                    result_data_dicts.append(
                        build_dataframe_row(
                            base_hash=base_pair.commit.commit_hash,
                            base_library=base_pair.commit.repository_name,
                            inter_hash=inter_pair.commit.commit_hash,
                            inter_library=inter_pair.commit.repository_name,
                            amount=inter_pair_amount_dict[inter_pair]
                        )
                    )

            return pd.DataFrame(result_data_dicts
                               ), report.head_commit.hash, str(
                                   report_path.stat().st_mtime_ns
                               )

        report_files = get_processed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study)
        )

        failed_report_files = get_failed_revisions_files(
            project_name, BlameReport,
            get_case_study_file_name_filter(case_study)
        )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report,
            lambda path: ReportFilename(path).commit_hash.hash,
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

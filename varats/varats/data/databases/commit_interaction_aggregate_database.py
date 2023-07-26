import typing as tp

import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_report import (
    gen_base_to_inter_commit_repo_pair_mapping,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.jupyterhelper.file import load_blame_report
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
)
from varats.utils.git_util import FullCommitHash


class SurvivingInteractionsDatabase(
    EvaluationDatabase,
    cache_id="survivng_interactions_data",
    column_types={
        "base_hash": 'str',
        "interactions": 'int32',
    }
):
    """Provides access to total interactions of commits."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_report(
            report_path: ReportFilepath
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_blame_report(report_path)
            base_inter_c_repo_pair_mapping = \
                gen_base_to_inter_commit_repo_pair_mapping(report)
            revision = report.head_commit

            def build_dataframe_row(chash: FullCommitHash,
                                    interactions: int) -> tp.Dict[str, tp.Any]:

                data_dict: tp.Dict[str, tp.Any] = {
                    'revision': revision.hash,
                    'time_id': commit_map.short_time_id(revision),
                    'base_hash': chash.hash,
                    'interactions': interactions
                }
                return data_dict

            result_data_dicts: tp.List[tp.Dict[str, tp.Any]] = []

            for base_pair in base_inter_c_repo_pair_mapping:
                inter_pair_amount_dict = base_inter_c_repo_pair_mapping[
                    base_pair]
                interactions_amount = sum(inter_pair_amount_dict.values())
                result_data_dicts.append(
                    build_dataframe_row(
                        chash=base_pair.commit.commit_hash,
                        interactions=interactions_amount
                    )
                )
            return pd.DataFrame(result_data_dicts
                               ), report.head_commit.hash, str(
                                   report_path.stat().st_mtime_ns
                               )

        report_files = get_processed_revisions_files(
            project_name,
            BlameReportExperiment,
            file_name_filter=get_case_study_file_name_filter(case_study)
        )

        failed_report_files = get_failed_revisions_files(
            project_name,
            BlameReportExperiment,
            file_name_filter=get_case_study_file_name_filter(case_study)
        )

        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report,
            lambda path: path.report_filename.commit_hash.hash,
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )
        return data_frame

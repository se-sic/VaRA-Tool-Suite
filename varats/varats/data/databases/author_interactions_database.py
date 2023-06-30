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
from varats.mapping.author_map import Author, generate_author_map
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import (
    get_local_project_git_path,
    get_primary_project_source,
)
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
)
from varats.utils.git_util import (
    create_commit_lookup_helper,
    UNCOMMITTED_COMMIT_HASH,
)


class AuthorInteractionsDatabase(
    EvaluationDatabase,
    cache_id="author_contribution_data_base",
    column_types={
        "author_name": 'str',
        "author_mail": 'str',
        "internal_interactions": 'int32',
        "external_interactions": 'int32'
    }
):
    """Provides access to internal and external interactions of authors."""

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

            def build_dataframe_row(
                author: Author, internal_interactions: int,
                external_interactions: int
            ) -> tp.Dict[str, tp.Any]:
                data_dict: tp.Dict[str, tp.Any] = {
                    'revision': revision.hash,
                    'time_id': commit_map.short_time_id(revision),
                    'author_name': author.name,
                    'author_mail': author.mail,
                    'internal_interactions': internal_interactions,
                    'external_interactions': external_interactions
                }
                return data_dict

            result_data_dicts: tp.Dict[Author, tp.Dict[str, tp.Any]] = {}
            amap = generate_author_map(project_name)
            repo_name = get_primary_project_source(project_name).local
            commit_lookup_helper = create_commit_lookup_helper(project_name)
            for base_pair in base_inter_c_repo_pair_mapping:
                if base_pair.commit.repository_name != repo_name:
                    # Skip interactions with submodules
                    continue
                inter_pair_dict = base_inter_c_repo_pair_mapping[base_pair]
                if base_pair.commit.commit_hash == UNCOMMITTED_COMMIT_HASH:
                    continue
                base_commit = commit_lookup_helper(base_pair.commit)
                base_author = amap.get_author(
                    base_commit.author.name, base_commit.author.email
                )
                if base_author is None:
                    amap.add_entry(
                        base_commit.author.name, base_commit.author.email
                    )
                    base_author = amap.get_author(
                        base_commit.author.name, base_commit.author.email
                    )
                internal_interactions = 0
                external_interactions = 0
                for inter_pair, interactions in inter_pair_dict.items():
                    if inter_pair.commit.commit_hash == UNCOMMITTED_COMMIT_HASH:
                        continue
                    inter_commit = commit_lookup_helper(inter_pair.commit)
                    inter_author = amap.get_author(
                        inter_commit.author.name, inter_commit.author.email
                    )
                    if base_author == inter_author:
                        internal_interactions += interactions
                    else:
                        external_interactions += interactions
                if base_author in result_data_dicts:
                    result_data_dicts[base_author]['internal_interactions'
                                                  ] += internal_interactions
                    result_data_dicts[base_author]['external_interactions'
                                                  ] += external_interactions
                else:
                    result_data_dicts[base_author] = build_dataframe_row(
                        base_author, internal_interactions,
                        external_interactions
                    )

            return pd.DataFrame(
                list(result_data_dicts.values())
            ), report.head_commit.hash, str(report_path.stat().st_mtime_ns)

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

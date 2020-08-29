"""Module for the base BlameInteractionDegreeDatabase class."""
import typing as tp
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.report import MetaReport
from varats.data.reports.blame_report import (
    BlameReport,
    generate_author_degree_tuples,
    generate_avg_time_distribution_tuples,
    generate_degree_tuples,
    generate_max_time_distribution_tuples,
)
from varats.data.reports.commit_report import CommitMap
from varats.data.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.jupyterhelper.file import load_blame_report
from varats.paper.case_study import CaseStudy, get_case_study_file_name_filter

MAX_TIME_BUCKET_SIZE = 1
AVG_TIME_BUCKET_SIZE = 1


class DegreeType(Enum):
    """Degree types of blame interaction data."""
    interaction = "interaction"
    author = "author"
    max_time = "max_time"
    avg_time = "avg_time"


class BlameInteractionDegreeDatabase(
    EvaluationDatabase,
    cache_id="blame_interaction_degree_data",
    columns=["degree_type", "degree", "amount", "fraction"]
):
    """Provides access to blame interaction degree data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.degree = df_layout.degree.astype('int64')
            df_layout.amount = df_layout.amount.astype('int64')
            df_layout.fraction = df_layout.fraction.astype('int64')
            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_blame_report(report_path)
            list_of_degree_occurrences = generate_degree_tuples(report)
            degrees, amounts = map(list, zip(*list_of_degree_occurrences))
            total = sum(amounts)

            list_of_author_degree_occurrences = generate_author_degree_tuples(
                report, project_name
            )
            author_degrees, author_amounts = map(
                list, zip(*list_of_author_degree_occurrences)
            )
            author_total = sum(author_amounts)

            list_of_max_time_deltas = generate_max_time_distribution_tuples(
                report, project_name, MAX_TIME_BUCKET_SIZE
            )
            max_time_buckets, max_time_amounts = map(
                list, zip(*list_of_max_time_deltas)
            )
            total_max_time_amounts = sum(max_time_amounts)

            list_of_avg_time_deltas = generate_avg_time_distribution_tuples(
                report, project_name, AVG_TIME_BUCKET_SIZE
            )
            avg_time_buckets, avg_time_amounts = map(
                list, zip(*list_of_avg_time_deltas)
            )
            total_avg_time_amounts = sum(avg_time_amounts)

            amount_of_entries = len(
                degrees + author_degrees + max_time_buckets + avg_time_buckets
            )

            return pd.DataFrame(
                {
                    'revision': [report.head_commit] * amount_of_entries,
                    'time_id': [commit_map.short_time_id(report.head_commit)] *
                               amount_of_entries,
                    'degree_type':
                        [DegreeType.interaction.value] * len(degrees) +
                        [DegreeType.author.value] * len(author_degrees) +
                        [DegreeType.max_time.value] * len(max_time_buckets) +
                        [DegreeType.avg_time.value] * len(avg_time_buckets),
                    'degree':
                        degrees + author_degrees + max_time_buckets +
                        avg_time_buckets,
                    'amount':
                        amounts + author_amounts + max_time_amounts +
                        avg_time_amounts,
                    'fraction':
                        np.concatenate([
                            np.divide(amounts, total),
                            np.divide(author_amounts, author_total),
                            np.divide(max_time_amounts, total_max_time_amounts),
                            np.divide(avg_time_amounts, total_avg_time_amounts)
                        ]),
                },
                index=range(0, amount_of_entries)
            ), report.head_commit, str(report_path.stat().st_mtime_ns)

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
            lambda path: MetaReport.get_commit_hash_from_result_file(path.name),
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

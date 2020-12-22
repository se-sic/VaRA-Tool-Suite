"""Module for the base BlameInteractionDegreeDatabase class."""
import typing as tp
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.data.reports.blame_report import (
    BlameReport,
    generate_author_degree_tuples,
    generate_avg_time_distribution_tuples,
    generate_max_time_distribution_tuples,
    generate_lib_dependent_degrees,
)
from varats.jupyterhelper.file import load_blame_report
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import MetaReport
from varats.revision.revisions import (
    get_failed_revisions_files,
    get_processed_revisions_files,
)
from varats.utils.git_util import create_commit_lookup_helper

MAX_TIME_BUCKET_SIZE = 1
AVG_TIME_BUCKET_SIZE = 1


class DegreeType(Enum):
    """Degree types of blame interaction data."""
    value: str

    interaction = "interaction"
    author = "author"
    max_time = "max_time"
    avg_time = "avg_time"


class BlameInteractionDegreeDatabase(
    EvaluationDatabase,
    cache_id="blame_interaction_degree_data",
    columns=[
        "degree_type", "base_lib", "inter_lib", "degree", "amount", "fraction"
    ]
):
    """Provides access to blame interaction degree data."""

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Any
    ) -> pd.DataFrame:
        commit_lookup = create_commit_lookup_helper(project_name)

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout.base_lib = df_layout.base_lib.astype('str')
            df_layout.inter_lib = df_layout.inter_lib.astype('str')
            df_layout.degree = df_layout.degree.astype('int64')
            df_layout.amount = df_layout.amount.astype('int64')
            df_layout.fraction = df_layout.fraction.astype('int64')

            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_blame_report(report_path)

            categorised_degree_occurrences = \
                generate_lib_dependent_degrees(report)

            def calc_total_amounts() -> int:
                total = 0

                for _, lib_dict \
                        in categorised_degree_occurrences.items():
                    for _, tuple_list in lib_dict.items():
                        for degree_amount_tuple in tuple_list:
                            total += degree_amount_tuple[1]
                return total

            total_amounts_of_all_libs = calc_total_amounts()

            list_of_author_degree_occurrences = \
                generate_author_degree_tuples(report, commit_lookup
                                              )
            author_degrees, author_amounts = map(
                list, zip(*list_of_author_degree_occurrences)
            )
            author_total = sum(author_amounts)

            list_of_max_time_deltas = generate_max_time_distribution_tuples(
                report, commit_lookup, MAX_TIME_BUCKET_SIZE
            )
            max_time_buckets, max_time_amounts = map(
                list, zip(*list_of_max_time_deltas)
            )
            total_max_time_amounts = sum(max_time_amounts)

            list_of_avg_time_deltas = generate_avg_time_distribution_tuples(
                report, commit_lookup, AVG_TIME_BUCKET_SIZE
            )
            avg_time_buckets, avg_time_amounts = map(
                list, zip(*list_of_avg_time_deltas)
            )
            total_avg_time_amounts = sum(avg_time_amounts)

            def build_dataframe_row(
                degree_type: DegreeType,
                degree: int,
                amount: int,
                total_amount: int,
                base_library: tp.Optional[str] = None,
                inter_library: tp.Optional[str] = None
            ) -> tp.Dict:

                data_dict: tp.Dict[str, tp.Any] = {
                    'revision': report.head_commit,
                    'time_id': commit_map.short_time_id(report.head_commit),
                    'degree_type': degree_type.value,
                    'base_lib': base_library,
                    'inter_lib': inter_library,
                    'degree': degree,
                    'amount': amount,
                    'fraction': np.divide(amount, total_amount)
                }
                return data_dict

            result_data_dicts: tp.List[tp.Dict] = []

            # Append interaction rows
            for base_lib_name, inter_lib_dict \
                    in categorised_degree_occurrences.items():

                for inter_lib_name, degree_amount_tuples in \
                        inter_lib_dict.items():

                    inter_degrees, inter_amounts = map(
                        list, zip(*degree_amount_tuples)
                    )

                    for i, _ in enumerate(inter_degrees):
                        degree = tp.cast(tp.List, inter_degrees)[i]
                        lib_amount = tp.cast(tp.List, inter_amounts)[i]

                        interaction_data_dict = build_dataframe_row(
                            degree_type=DegreeType.interaction,
                            degree=degree,
                            amount=lib_amount,
                            total_amount=total_amounts_of_all_libs,
                            base_library=base_lib_name,
                            inter_library=inter_lib_name,
                        )
                        result_data_dicts.append(interaction_data_dict)

            def append_rows_of_degree_type(
                degree_type: DegreeType,
                degrees: tp.List[int],
                amounts: tp.List[int],
                sum_amounts: int,
            ):
                for k, _ in enumerate(degrees):
                    data_dict = build_dataframe_row(
                        degree_type=degree_type,
                        degree=degrees[k],
                        amount=amounts[k],
                        total_amount=sum_amounts
                    )
                    result_data_dicts.append(data_dict)

            # Append author rows
            append_rows_of_degree_type(
                degree_type=DegreeType.author,
                degrees=tp.cast(tp.List, author_degrees),
                amounts=tp.cast(tp.List, author_amounts),
                sum_amounts=tp.cast(int, author_total)
            )

            # Append max_time rows
            append_rows_of_degree_type(
                degree_type=DegreeType.max_time,
                degrees=tp.cast(tp.List, max_time_buckets),
                amounts=tp.cast(tp.List, max_time_amounts),
                sum_amounts=tp.cast(int, total_max_time_amounts)
            )

            # Append avg_time rows
            append_rows_of_degree_type(
                degree_type=DegreeType.avg_time,
                degrees=tp.cast(tp.List, avg_time_buckets),
                amounts=tp.cast(tp.List, avg_time_amounts),
                sum_amounts=tp.cast(int, total_avg_time_amounts)
            )

            return pd.DataFrame(result_data_dicts), report.head_commit, str(
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
            lambda path: MetaReport.get_commit_hash_from_result_file(path.name),
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

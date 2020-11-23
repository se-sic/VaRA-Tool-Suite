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
    generate_degree_tuples,
    generate_max_time_distribution_tuples,
    is_multi_repository_report,
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
        "degree_type", "degree", "amount", "fraction", "base_lib", "inter_lib",
        "lib_degree", "lib_amount", "lib_fraction"
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
            df_layout.degree = df_layout.degree.astype('int64')
            df_layout.amount = df_layout.amount.astype('int64')
            df_layout.fraction = df_layout.fraction.astype('int64')
            df_layout.base_lib = df_layout.base_lib.astype('str')
            df_layout.inter_lib = df_layout.inter_lib.astype('str')
            df_layout.lib_degree = df_layout.lib_degree.astype('int64')
            df_layout.lib_amount = df_layout.lib_amount.astype('int64')
            df_layout.lib_fraction = df_layout.lib_fraction.astype('int64')

            return df_layout

        def create_data_frame_for_report(
            report_path: Path
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_blame_report(report_path)

            # TODO: Use categorised degrees and amounts only if the report has
            #  multiple libs
            # TODO: Find better way to make multi_repo_report check
            multi_repo_report: bool = is_multi_repository_report(report)

            categorised_list_of_degree_occurrences = \
                generate_lib_dependent_degrees(report)

            total_amounts_of_all_libs = 0

            for base_name, lib_dict \
                    in categorised_list_of_degree_occurrences.items():
                for lib_name, tuple_list in lib_dict.items():
                    for degree_amount_tuple in tuple_list:
                        total_amounts_of_all_libs += degree_amount_tuple[1]

            list_of_degree_occurrences = generate_degree_tuples(report)
            degrees, amounts = map(list, zip(*list_of_degree_occurrences))
            total = sum(amounts)

            list_of_author_degree_occurrences = generate_author_degree_tuples(
                report, commit_lookup
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

            # TODO: calculate amount_of_entries
            amount_of_entries = len(
                degrees + author_degrees + max_time_buckets + avg_time_buckets
            )

            # TODO: Add degree_type etc. to dataframe rows
            def build_dataframe_row(
                base_library: str, inter_library: str, lib_degree: int,
                lib_amount: int
            ) -> tp.Dict:

                data_dict: tp.Dict[str, tp.Any] = {
                    'revision':
                        report.head_commit,
                    'time_id':
                        commit_map.short_time_id(report.head_commit),
                    'base_lib':
                        base_library,
                    'inter_lib':
                        inter_library,
                    'lib_degree':
                        lib_degree,
                    'lib_amount':
                        lib_amount,
                    'lib_fraction':
                        np.divide(lib_amount, total_amounts_of_all_libs)
                }
                return data_dict

            result_data_dicts: tp.List[tp.Dict] = []

            for base_lib_name, inter_lib_dict \
                    in categorised_list_of_degree_occurrences.items():

                for inter_lib_name, degree_amount_tuples in \
                        inter_lib_dict.items():

                    inter_degrees, inter_amounts = map(
                        list, zip(*degree_amount_tuples)
                    )
                    # TODO: simplify with zip()
                    for x in range(len(inter_degrees)):
                        current_data_dict = build_dataframe_row(
                            base_lib_name,
                            inter_lib_name,
                            tp.cast(tp.List, inter_degrees)[x],
                            tp.cast(tp.List, inter_amounts)[x],
                        )
                        result_data_dicts.append(current_data_dict)

            # TODO: remove testing rows
            fire_lib_test_one = build_dataframe_row(
                "fire_lib", "Elementalist", 5, 24
            )
            fire_lib_test_two = build_dataframe_row(
                "fire_lib", "Elementalist", 6, 42
            )
            result_data_dicts.append(fire_lib_test_one)
            result_data_dicts.append(fire_lib_test_two)

            df = pd.DataFrame(result_data_dicts)
            return df, report.head_commit, str(report_path.stat().st_mtime_ns)

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

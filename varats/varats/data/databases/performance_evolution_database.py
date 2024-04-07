"""Database for evaluating performance evolution of configurable systems."""
import typing as tp

import pandas as pd

from varats.base.configuration import PlainCommandlineConfiguration
from varats.data.cache_helper import build_cached_report_table
from varats.data.databases.evaluationdatabase import EvaluationDatabase
from varats.experiments.base.time_workloads import TimeWorkloads
from varats.jupyterhelper.file import load_wl_time_report_aggregate
from varats.mapping.commit_map import CommitMap
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.report import ReportFilepath
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_failed_revisions_files,
)
from varats.utils.config import load_configuration_map_for_case_study


class PerformanceEvolutionDatabase(
    EvaluationDatabase,
    cache_id="performance_evolution_data",
    column_types={
        'config_id': 'int64',
        'wall_clock_time': 'object'
    }
):

    @classmethod
    def _load_dataframe(
        cls, project_name: str, commit_map: CommitMap,
        case_study: tp.Optional[CaseStudy], **kwargs: tp.Dict[str, tp.Any]
    ) -> pd.DataFrame:
        assert case_study is not None

        def create_dataframe_layout() -> pd.DataFrame:
            df_layout = pd.DataFrame(columns=cls.COLUMNS)
            df_layout = df_layout.astype(cls.COLUMN_TYPES)
            return df_layout

        def create_data_frame_for_report(
            report_path: ReportFilepath
        ) -> tp.Tuple[pd.DataFrame, str, str]:
            report = load_wl_time_report_aggregate(report_path)
            assert len(report.workload_names()) == 1
            workload = next(iter(report.workload_names()))

            commit_hash = report.filename.commit_hash
            df = pd.DataFrame({
                'revision': commit_hash.hash,
                'time_id': commit_map.short_time_id(commit_hash),
                'config_id': report.filename.config_id,
            },
                              columns=cls.COLUMNS,
                              index=[0])
            df = df.astype(cls.COLUMN_TYPES)
            # workaround to store a list in a data frame
            df.at[0, "wall_clock_time"] = report.measurements_wall_clock_time(
                workload
            )

            return df, commit_hash.hash, str(report_path.stat().st_mtime_ns)

        configs = load_configuration_map_for_case_study(
            get_paper_config(), case_study, PlainCommandlineConfiguration
        )
        report_files: tp.List[ReportFilepath] = []
        for config_id in configs.ids():
            report_files.extend(
                get_processed_revisions_files(
                    project_name,
                    TimeWorkloads,
                    file_name_filter=get_case_study_file_name_filter(
                        case_study
                    ),
                    config_id=config_id
                )
            )

        failed_report_files: tp.List[ReportFilepath] = []
        for config_id in configs.ids():
            failed_report_files.extend(
                get_failed_revisions_files(
                    project_name,
                    TimeWorkloads,
                    file_name_filter=get_case_study_file_name_filter(
                        case_study
                    ),
                    config_id=config_id
                )
            )

        # cls.CACHE_ID is set by superclass
        # pylint: disable=E1101
        data_frame = build_cached_report_table(
            cls.CACHE_ID, project_name, report_files, failed_report_files,
            create_dataframe_layout, create_data_frame_for_report,
            lambda path: path.report_filename.commit_hash.hash,
            lambda path: str(path.stat().st_mtime_ns),
            lambda a, b: int(a) > int(b)
        )

        return data_frame

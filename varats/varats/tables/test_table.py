"""Module for feature performance analysis tables."""
import logging
import typing as tp

import pandas as pd
from pandas import CategoricalDtype

from varats.experiments.vara.test_runner import TestRunner
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.data.reports.performance_influence_trace_report import (
    PerfInfluenceTraceReport,
    PerfInfluenceTraceReportAggregate,
    WorkloadSpecificPITReportAggregate
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import CommitHash

LOG = logging.Logger(__name__)


class TestTable(
    Table, table_name="test_table"
):
    """Table comparing the performance of features across releases for each
    workload."""


    @staticmethod
    def sort_revisions(case_study: CaseStudy,
                       revisions: tp.List[CommitHash]) -> tp.List[CommitHash]:
        """Sorts revision by time."""
        commit_map = get_commit_map(case_study.project_name)
        project_revisions = sorted(case_study.revisions, key=commit_map.time_id)
        return [
            h.to_short_commit_hash()
            for h in project_revisions
            if h.to_short_commit_hash() in revisions
        ]
    
    def get_performance_entries(
            self,
            perf_report: PerfInfluenceTraceReport
    ) -> tp.Dict[str, int]:
        perfor: tp.Dict[str, int] = {}

        reg_int_ent = perf_report.region_interaction_entries
        for entry in reg_int_ent:
            perfor[perf_report._translate_interaction(entry.interaction)] = entry.time

        return perfor


    def get_feature_performances_row(
        self,
        case_study: CaseStudy,
        perf_report_agg: PerfInfluenceTraceReportAggregate,
        workload: str,
    ) -> tp.Dict[str, tp.Union[str, CommitHash, tp.Dict[str, int],
                               tp.Optional[int]]]:
        """Returns a dict with information about feature performances from a
        TEFReport for a given workload."""
        perf_report = perf_report_agg.reports(workload)
        if len(perf_report) > 1:
            print(
                "Table can currently handle only one TEFReport per "
                "revision, workload and config. Ignoring others."
            )
        feature_performances = self.get_performance_entries(perf_report[0])
        return {
            "Project": case_study.project_name,
            "Revision": perf_report_agg.filename.commit_hash,
            "Workload": workload,
            "Config_ID": perf_report_agg.filename.config_id,
            "Timestamp_Unit": perf_report[0].timestamp_unit,
            **feature_performances,
        }

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        df = pd.DataFrame()

        for case_study in get_loaded_paper_config().get_all_case_studies():
            # Parse reports
            report_files = get_processed_revisions_files(
                case_study.project_name,
                TestRunner,
                PerfInfluenceTraceReport,
                get_case_study_file_name_filter(case_study),
                only_newest=False,
            )

            workloads = set()
            revisions = set()

            for report_filepath in report_files:
                perf_report_agg = WorkloadSpecificPITReportAggregate(
                    report_filepath.full_path()
                )
                report_file = perf_report_agg.filename
                revisions.add(report_file.commit_hash)

                for workload in perf_report_agg.workload_names():
                    workloads.add(workload)
                    df2 = pd.DataFrame([self.get_feature_performances_row(
                            case_study, perf_report_agg, workload
                        )])
                    df = pd.concat([df, df2],
                        ignore_index=True,
                    )

            if not df.empty:
                # Sort revisions so that we can compare consecutive releases
                # later
                sorted_revisions = self.sort_revisions(
                    case_study, list(revisions)
                )
                sorted_revisions = CategoricalDtype(
                    sorted_revisions, ordered=True
                )
                df['Revision'] = df['Revision'].astype(sorted_revisions)
            else:
                print("Empty DataFrame")

        df.sort_values(["Project", "Revision", "Workload", "Config_ID"],
                       inplace=True)
        df.set_index(
            ["Project"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = ("c|" * len(df.columns)) + "c"

        return dataframe_to_table(
            df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class TestTableGenerator(
    TableGenerator, generator_name="test-analysis", options=[]
):
    """Generates a feature performance analysis table for the selected case
    study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            TestTable(
                self.table_config, **self.table_kwargs
            )
        ]


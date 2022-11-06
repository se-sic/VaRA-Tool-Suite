"""Module for feature performance analysis tables."""
import logging
import typing as tp
from pathlib import Path
from pprint import pprint

import more_itertools
import numpy as np
import pandas as pd

from varats.experiment.workload_util import get_workload_label
from varats.experiments.vara.feature_perf_runner import FeaturePerfRunner
from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.project.project_util import (
    get_local_project_git,
    get_project_cls_by_name,
    get_local_project_git_path,
)
from varats.report.gnu_time_report import (
    TimeReportAggregate,
    WLTimeReportAggregate,
)
from varats.report.tef_report import (
    TEFReport,
    TEFReportAggregate,
    WorkloadAndConfigSpecificTEFReportAggregate,
    TraceEventType,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import calc_repo_loc, num_commits, num_authors

LOG = logging.Logger(__name__)


class FeaturePerformanceAnalysisTable(
    Table, table_name="feature_perf_analysis_table"
):
    """
    Table showing ...

    TODO
    """

    @staticmethod
    def get_feature_durations_from_tef_report(
        tef_report: TEFReport
    ) -> tp.Dict[str, int]:
        begin_events = {
            trace_event.name: list() for trace_event in tef_report.trace_events
        }

        # TODO: Interactions (FR(x,y)) and Nesting

        feature_durations = dict()

        for trace_event in tef_report.trace_events:
            if trace_event.category == "Feature":
                if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                    begin_events[trace_event.name].append(trace_event)
                elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                    current_duration = feature_durations.get(
                        trace_event.name, 0
                    )
                    end_timestamp = trace_event.timestamp
                    begin_timestamp = begin_events[trace_event.name
                                                  ].pop().timestamp
                    feature_durations[
                        trace_event.name
                    ] = current_duration + end_timestamp - begin_timestamp

        return feature_durations

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        internal_df = pd.DataFrame()
        output_df = pd.DataFrame()

        for case_study in case_studies:
            project_name = case_study.project_name

            # Parse reports
            report_files = get_processed_revisions_files(
                project_name,
                FeaturePerfRunner,
                TEFReport,
                get_case_study_file_name_filter(case_study),
                only_newest=False
            )

            workloads = list()
            revisions = list()

            for report_filepath in report_files:
                agg_tef_report = WorkloadAndConfigSpecificTEFReportAggregate(
                    report_filepath.full_path()
                )
                report_file = agg_tef_report.filename

                for key in agg_tef_report.workload_and_config_ids():
                    tef_report = agg_tef_report.reports(key)
                    if len(tef_report) > 1:
                        print(
                            "Table can currently handle only one TEFReport per "
                            "release, workload and config. Ignoring others."
                        )
                    feature_durations = self.get_feature_durations_from_tef_report(
                        tef_report[0]
                    )
                    workload, config_id = key
                    if workload not in workloads:
                        workloads.append(workload)
                    revision = str(report_file.commit_hash)
                    if revision not in revisions:
                        revisions.append(revision)
                    new_row = {
                        "Project": project_name,
                        "Revision": revision,
                        "Workload": workload,
                        "Config ID": config_id,
                        "Feature Durations": feature_durations,
                    }

                    internal_df = internal_df.append(new_row, ignore_index=True)

            # Compare reports
            for workload in workloads:
                # Use sliding window to always compare two consecutive releases
                # TODO: Only compare consecutive releases
                for revision_1, revision_2 in more_itertools.windowed(
                    revisions, 2
                ):
                    if revision_2 is not None:
                        revision_1_data = internal_df[
                            (internal_df["Project"] == case_study.project_name)
                            & (internal_df["Workload"] == workload) &
                            (internal_df["Revision"] == revision_1)]
                        revision_2_data = internal_df[
                            (internal_df["Project"] == case_study.project_name)
                            & (internal_df["Workload"] == workload) &
                            (internal_df["Revision"] == revision_2)]
                        feature_durations_df_revision_1 = pd.DataFrame.from_records(
                            revision_1_data["Feature Durations"].values
                        )
                        feature_durations_df_revision_2 = pd.DataFrame.from_records(
                            revision_2_data["Feature Durations"].values
                        )
                        # TODO: Does using mean make sense here? Do we need to filter configs first?
                        feature_durations_df_revision_1_mean = feature_durations_df_revision_1.mean(
                        )
                        feature_durations_df_revision_2_mean = feature_durations_df_revision_2.mean(
                        )
                        diff = feature_durations_df_revision_2_mean - feature_durations_df_revision_1_mean
                        output_df = output_df.append(
                            dict({
                                "Project": project_name,
                                "Workload": workload,
                                "Revision 1": revision_1,
                                "Revision 2": revision_2,
                            }, **diff),
                            ignore_index=True
                        )

        internal_df.sort_values(["Project"], inplace=True)
        internal_df.set_index(
            ["Project"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = "llr|rr|r|r"

        return dataframe_to_table(
            output_df, table_format, wrap_table, wrap_landscape=True, **kwargs
        )


class CaseStudyMetricsTableGenerator(
    TableGenerator, generator_name="feature-perf-analysis", options=[]
):
    """Generates a cs-metrics table for the selected case study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerformanceAnalysisTable(
                self.table_config, **self.table_kwargs
            )
        ]

"""Module for feature performance analysis tables."""
import logging
import typing as tp

import pandas as pd
from pandas import CategoricalDtype

from varats.experiments.vara.feature_perf_runner import FeaturePerfRunner
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.tef_report import (
    TEFReport,
    WorkloadSpecificTEFReportAggregate,
    TraceEventType,
    TraceEvent,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.utils.git_util import CommitHash

LOG = logging.Logger(__name__)


class FeaturePerformanceAnalysisTable(
    Table, table_name="feature_perf_analysis_table"
):
    """Table comparing the performance of features across releases for each
    workload."""

    @staticmethod
    def get_interactions_from_fr_string(interactions: str) -> str:
        """Convert the feature strings in a TEFReport from FR(x,y) to x*y,
        similar to the format used by SPLConqueror."""
        interactions = (
            interactions.replace("FR", "").replace("(", "").replace(")", "")
        )
        interactions_list = interactions.split(",")
        # Ignore interactions with base, but do not remove base if it's the only
        # feature
        if "Base" in interactions_list and len(interactions_list) > 1:
            interactions_list.remove("Base")
        # Features cannot interact with itself, so remove duplicastes
        interactions_list = list(set(interactions_list))

        interactions_str = "*".join(interactions_list)

        return interactions_str

    @staticmethod
    def get_feature_performance_from_tef_report(
        tef_report: TEFReport,
    ) -> tp.Dict[str, int]:
        """Extract feature performance from a TEFReport."""
        open_events: tp.List[TraceEvent] = []

        feature_performances: tp.Dict[str, int] = {}

        for trace_event in tef_report.trace_events:
            if trace_event.category == "Feature":
                if (
                    trace_event.event_type ==
                    TraceEventType.DURATION_EVENT_BEGIN
                ):
                    open_events.append(trace_event)
                elif (
                    trace_event.event_type == TraceEventType.DURATION_EVENT_END
                ):
                    opening_event = open_events.pop()

                    end_timestamp = trace_event.timestamp
                    begin_timestamp = opening_event.timestamp

                    # Subtract feature duration from parent duration such that
                    # it is not counted twice, similar to behavior in
                    # Performance-Influence models.
                    interactions = [event.name for event in open_events]
                    if open_events:
                        # Parent is equivalent to interaction of all open
                        # events.
                        interaction_string = FeaturePerformanceAnalysisTable\
                            .get_interactions_from_fr_string(
                                ",".join(interactions)
                            )
                        if interaction_string in feature_performances:
                            feature_performances[interaction_string] -= (
                                end_timestamp - begin_timestamp
                            )
                        else:
                            feature_performances[interaction_string] = -(
                                end_timestamp - begin_timestamp
                            )

                    interaction_string = FeaturePerformanceAnalysisTable\
                        .get_interactions_from_fr_string(
                            ",".join(interactions + [trace_event.name])
                        )

                    current_performance = feature_performances.get(
                        interaction_string, 0
                    )
                    feature_performances[interaction_string] = (
                        current_performance + end_timestamp - begin_timestamp
                    )

        return feature_performances

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

    def get_feature_performances_row(
        self,
        case_study: CaseStudy,
        agg_tef_report: WorkloadSpecificTEFReportAggregate,
        workload: str,
    ) -> tp.Dict[str, tp.Union[str, CommitHash, tp.Dict[str, int],
                               tp.Optional[int]]]:
        """Returns a dict with information about feature performances from a
        TEFReport for a given workload."""
        tef_report = agg_tef_report.reports(workload)
        if len(tef_report) > 1:
            print(
                "Table can currently handle only one TEFReport per "
                "revision, workload and config. Ignoring others."
            )
        feature_performances = self.get_feature_performance_from_tef_report(
            tef_report[0]
        )
        return {
            "Project": case_study.project_name,
            "Revision": agg_tef_report.filename.commit_hash,
            "Workload": workload,
            "Config_ID": agg_tef_report.filename.config_id,
            "Timestamp_Unit": tef_report[0].timestamp_unit,
            **feature_performances,
        }

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        df = pd.DataFrame()

        for case_study in get_loaded_paper_config().get_all_case_studies():
            # Parse reports
            report_files = get_processed_revisions_files(
                case_study.project_name,
                FeaturePerfRunner,
                TEFReport,
                get_case_study_file_name_filter(case_study),
                only_newest=False,
            )

            workloads = set()
            revisions = set()

            for report_filepath in report_files:
                agg_tef_report = WorkloadSpecificTEFReportAggregate(
                    report_filepath.full_path()
                )
                report_file = agg_tef_report.filename
                revisions.add(report_file.commit_hash)

                for workload in agg_tef_report.workload_names():
                    workloads.add(workload)
                    df = df.append(
                        self.get_feature_performances_row(
                            case_study, agg_tef_report, workload
                        ),
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


class FeaturePerformanceAnalysisTableGenerator(
    TableGenerator, generator_name="feature-perf-analysis", options=[]
):
    """Generates a feature performance analysis table for the selected case
    study(ies)."""

    def generate(self) -> tp.List[Table]:
        return [
            FeaturePerformanceAnalysisTable(
                self.table_config, **self.table_kwargs
            )
        ]

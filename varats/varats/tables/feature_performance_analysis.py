"""Module for feature performance analysis tables."""
import logging
import typing as tp

import more_itertools
import pandas as pd

from varats.experiments.vara.feature_perf_runner import FeaturePerfRunner
from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.report.tef_report import (
    TEFReport,
    WorkloadAndConfigSpecificTEFReportAggregate,
    TraceEventType,
    TraceEvent,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator

LOG = logging.Logger(__name__)


class FeaturePerformanceAnalysisTable(
    Table, table_name="feature_perf_analysis_table"
):
    """Table comparing the performance of features across releases for each
    workload."""

    @staticmethod
    def get_interactions_from_fr_string(interactions: str):
        """Convert the feature strings in a TEFReport from FR(x,y) to x*y,
        similar to the format used by SPLConqueror."""
        interactions = interactions.replace("FR",
                                            "").replace("(",
                                                        "").replace(")", "")
        interactions = interactions.split(",")
        # Ignore interactions with base, but do not remove base if it's the only feature
        if "Base" in interactions and len(interactions) > 1:
            interactions.remove("Base")
        # Features cannot interact with itself, so remove duplicastes
        interactions = list(set(interactions))

        interactions = "*".join(interactions)

        return interactions

    @staticmethod
    def get_feature_performance_from_tef_report(
        tef_report: TEFReport
    ) -> tp.Dict[str, int]:
        """Extract feature performance from a TEFReport."""
        open_events: tp.List[TraceEvent] = list()

        feature_performances = dict()

        for trace_event in tef_report.trace_events:
            if trace_event.category == "Feature":
                if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                    open_events.append(trace_event)
                elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                    opening_event = open_events.pop()
                    assert (opening_event.name == trace_event.name)

                    end_timestamp = trace_event.timestamp
                    begin_timestamp = opening_event.timestamp

                    interactions = list()
                    for event in open_events:
                        interaction_string = FeaturePerformanceAnalysisTable.get_interactions_from_fr_string(
                            event.name
                        )
                        if event in feature_performances:
                            feature_performances[interaction_string] -= (
                                end_timestamp - begin_timestamp
                            )
                        else:
                            feature_performances[interaction_string] = -(
                                end_timestamp - begin_timestamp
                            )
                        interactions.append(event.name)

                    interaction_string = FeaturePerformanceAnalysisTable.get_interactions_from_fr_string(
                        ",".join(interactions + [trace_event.name])
                    )

                    current_performance = feature_performances.get(
                        interaction_string, 0
                    )
                    feature_performances[
                        interaction_string
                    ] = current_performance + end_timestamp - begin_timestamp

        return feature_performances

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
                    feature_performances = self.get_feature_performance_from_tef_report(
                        tef_report[0]
                    )
                    workload, config_id = key
                    if workload not in workloads:
                        workloads.append(workload)
                    revision = report_file.commit_hash
                    if revision not in revisions:
                        revisions.append(revision)
                    new_row = {
                        "Project": project_name,
                        "Revision": revision,
                        "Workload": workload,
                        "Config ID": config_id,
                        "Feature Performances": feature_performances,
                    }

                    internal_df = internal_df.append(new_row, ignore_index=True)

            # Sort revisions so that we can compare consecutive releases
            commit_map = get_commit_map(project_name)
            project_revisions = sorted(
                case_study.revisions, key=commit_map.time_id, reverse=True
            )
            revisions = [
                h.to_short_commit_hash()
                for h in project_revisions
                if h.to_short_commit_hash() in revisions
            ]

            # Compare reports
            for workload in workloads:
                # Use sliding window to always compare two consecutive releases
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
                        feature_performances_df_revision_1 = pd.DataFrame.from_records(
                            revision_1_data["Feature Performances"].values
                        )
                        feature_performances_df_revision_2 = pd.DataFrame.from_records(
                            revision_2_data["Feature Performances"].values
                        )
                        # TODO: Does using mean make sense here?
                        # TODO: Should we only respect the minimal configs for this option/interaction or is the mean over all configs in which the option is active (!= NaN) ok?
                        feature_performances_df_revision_1_mean = feature_performances_df_revision_1.mean(
                        )
                        feature_performances_df_revision_2_mean = feature_performances_df_revision_2.mean(
                        )
                        diff = feature_performances_df_revision_2_mean - feature_performances_df_revision_1_mean
                        output_df = output_df.append(
                            dict({
                                "Project": project_name,
                                "Workload": workload,
                                "Revision 1": revision_1,
                                "Revision 2": revision_2,
                            }, **diff),
                            ignore_index=True
                        )

        output_df.sort_values(["Project"], inplace=True)
        output_df.set_index(
            ["Project"],
            inplace=True,
        )

        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["column_format"] = ("c|" * len(output_df.columns)) + "c"

        return dataframe_to_table(
            output_df, table_format, wrap_table, wrap_landscape=True, **kwargs
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

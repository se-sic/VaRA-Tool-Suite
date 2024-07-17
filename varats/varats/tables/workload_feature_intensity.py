import logging
import typing as tp
from collections import defaultdict

import click

from varats.data.databases.feature_perf_precision_database import (
    get_interactions_from_fr_string,
)
from varats.data.reports.FeatureIntensity import WorkloadFeatureIntensityReport
from varats.experiments.vara.workload_feature_intensity import (
    WorkloadFeatureIntensityExperiment,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.tef_report import (
    TEFReportAggregate,
    TEFReport,
    TraceEvent,
    TraceEventType,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.table.table import Table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import make_cli_option

LOG = logging.getLogger(__name__)


def get_feature_regions_from_tef_report(
    tef_report: TEFReport,
) -> tp.Dict[tp.Tuple[str, tp.Tuple[int, ...]], int]:
    """Extract feature regions from a TEFReport."""
    open_events: tp.List[TraceEvent] = []

    feature_performances: tp.Dict[tp.Tuple[str, tp.Tuple[int, ...]],
                                  int] = defaultdict(int)

    def get_matching_event(
        open_events: tp.List[TraceEvent], closing_event: TraceEvent
    ) -> tp.Optional[TraceEvent]:
        for event in open_events:
            if (
                event.uuid == closing_event.uuid and
                event.pid == closing_event.pid and
                event.tid == closing_event.tid
            ):
                open_events.remove(event)
                return event

        LOG.debug(
            f"Could not find matching start for Event {repr(closing_event)}."
        )

        return None

    found_missing_open_event = False
    for trace_event in tef_report.trace_events:
        if trace_event.category == "Feature":
            if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                # insert event at the top of the list
                open_events.insert(0, trace_event)
            elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                opening_event = get_matching_event(open_events, trace_event)
                if not opening_event:
                    found_missing_open_event = True
                    continue

                interaction_names = [event.name for event in open_events]
                region_ids = tuple([event.uuid for event in open_events])

                interaction_string = get_interactions_from_fr_string(
                    ",".join(interaction_names + [trace_event.name])
                )

                feature_performances[(interaction_string, region_ids)] += 1

    if open_events:
        LOG.error("Not all events have been correctly closed.")
        LOG.debug(f"Events = {open_events}.")

    if found_missing_open_event:
        LOG.error("Not all events have been correctly opened.")

    return feature_performances


class WorkloadIntensityTable(Table, table_name="workload_intensity"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_study: CaseStudy = self.table_kwargs.pop("case_study")

        for config_id in case_study.get_config_ids_for_revision(
            case_study.revisions[0]
        ):
            project_name = case_study.project_name
            report_files = get_processed_revisions_files(
                project_name,
                WorkloadFeatureIntensityExperiment,
                WorkloadFeatureIntensityReport,
                get_case_study_file_name_filter(case_study),
                config_id=config_id
            )

            if len(report_files) > 1:
                raise AssertionError("Should only be one")
            if not report_files:
                print(
                    f"Could not find workload intensity data for {project_name=}"
                    f". {config_id=}"
                )
                return None

            reports = WorkloadFeatureIntensityReport(
                report_files[0].full_path()
            )

            for report in reports.reports():
                pass

        pass


class WorkloadIntensityTableGenerator(
    TableGenerator, generator_name="workload-intensity", options=[]
):

    def generate(self) -> tp.List[Table]:
        case_studies = get_loaded_paper_config().get_all_case_studies()
        return [
            WorkloadIntensityTable(
                self.table_config, case_study=cs, **self.table_kwargs
            ) for cs in case_studies if cs.project_name == "SynthCTCRTP"
        ]

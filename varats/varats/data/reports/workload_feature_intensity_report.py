import logging
import typing as tp
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from varats.data.databases.feature_perf_precision_database import (
    get_interactions_from_fr_string,
)
from varats.report.report import BaseReport
from varats.report.tef_report import TEFReport, TraceEvent, TraceEventType

LOG = logging.getLogger(__name__)


class WorkloadFeatureIntensityReport(
    BaseReport, shorthand="WFIR", file_type="zip"
):
    """Report that aggregates the feature intensities for different binaries and
    workloads."""

    def __extract_workload_name_from_report(self, report: TEFReport) -> str:
        return report.filename.filename.split("/")[-1].split("_")[2]

    def __get_feature_regions_from_tef_report(
        tef_report: TEFReport,
    ) -> tp.Dict[tp.Tuple[str, tp.Tuple[int, ...]], int]:
        """Extract feature regions from a TEFReport."""
        open_events: tp.List[TraceEvent] = []

        feature_intensities: tp.Dict[tp.Tuple[str, tp.Tuple[int, ...]],
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

                    feature_intensities[(interaction_string, region_ids)] += 1

        if open_events:
            LOG.error("Not all events have been correctly closed.")
            LOG.debug(f"Events = {open_events}.")

        if found_missing_open_event:
            LOG.error("Not all events have been correctly opened.")

        return feature_intensities

    def __init__(self, path: Path):
        super().__init__(path)

        self.__reports: tp.Dict[str, tp.List[TEFReport]] = defaultdict(list)

        # Unpack zip file to temporary directory
        with ZipFile(path, "r") as archive:
            for name in archive.namelist():
                # Ignore directories
                if name.endswith("/"):
                    continue

                # Extract binary name from file name
                binary_name = name.split("/")[0]

                # Extract file to temporary directory and create report
                with TemporaryDirectory() as tmpdir:
                    archive.extract(name, tmpdir)
                    self.__reports[binary_name].append(
                        TEFReport(Path(tmpdir) / name)
                    )

    def binaries(self) -> tp.List[str]:
        return list(self.__reports.keys())

    def workloads_for_binary(self, binary: str) -> tp.List[str]:
        # Extract workloads from report file names
        # Report filenames are in format "feature_intensity_<workload>_0.json"
        return [
            self.__extract_workload_name_from_report(report)
            for report in self.__reports[binary]
        ]

    def reports_for_binary(self, binary: str) -> tp.Dict[str, TEFReport]:
        return {
            self.__extract_workload_name_from_report(report): report
            for report in self.__reports[binary]
        }

    def feature_intensities_for_binary(
        self, binary: str
    ) -> tp.Dict[str, tp.Dict[str, int]]:
        pass

    def region_intensities_for_binary(
        self, binary: str
    ) -> tp.Dict[tp.Tuple[str, tp.Tuple[int, ...]], int]:
        pass

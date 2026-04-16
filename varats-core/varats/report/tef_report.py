"""Report module to create and handle trace event format files, e.g., created
with chrome tracing."""

import logging
import re
import typing as tp
from enum import Enum
from pathlib import Path

import ijson.backends.yajl2_c as ijson

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate

LOG = logging.getLogger(__name__)


class TraceEventType(Enum):
    """Enum to represent the different event types of trace format events,
    defined by the Trace Event Format specification."""

    value: str  # pylint: disable=invalid-name

    DURATION_EVENT_BEGIN = 'B'
    DURATION_EVENT_END = 'E'
    COMPLETE_EVENT = 'X'
    INSTANT_EVENT = 'i'
    COUNTER_EVENT = 'C'
    ASYNC_EVENT_START = 'b'
    ASYNC_EVENT_INSTANT = 'n'
    ASYNC_EVENT_END = 'e'
    FLOW_EVENT_START = 's'
    FLOW_EVENT_STEP = 't'
    FLOW_EVENT_END = 'f'
    SAMPLE_EVENT = 'P'

    @staticmethod
    def parse_event_type(raw_event_type: str) -> 'TraceEventType':
        """Parses a raw string that represents a trace-format event type and
        converts it to the corresponding enum value."""
        for trace_event_type in TraceEventType:
            if trace_event_type.value == raw_event_type:
                return trace_event_type

        raise LookupError("Could not find correct trace event type")

    def __str__(self) -> str:
        return str(self.value)


class TraceEvent():
    """Represents a trace event that was captured during the analysis of a
    target program."""

    __uuid: int

    def __init__(
        self, json_trace_event: tp.Dict[str, tp.Any], name_id: int,
        name_id_mapper: 'TEFReport.NameIDMapper'
    ) -> None:
        self.__name_id_mapper = name_id_mapper
        self.__name_id = name_id
        self.__category = str(json_trace_event["cat"])
        self.__event_type = TraceEventType.parse_event_type(
            json_trace_event["ph"]
        )
        self.__tracing_clock_timestamp = int(json_trace_event["ts"])
        self.__pid = int(json_trace_event["pid"])
        self.__tid = int(json_trace_event["tid"])

        if "UUID" in json_trace_event:
            self.__uuid = int(json_trace_event["UUID"])
        elif "ID" in json_trace_event:
            self.__uuid = int(json_trace_event["ID"])
        else:
            LOG.critical("Could not parse UUID/ID from trace event")
            self.__uuid: int = 0

    @property
    def name(self) -> str:
        return self.__name_id_mapper.infer_name(self.__name_id)

    @property
    def category(self) -> str:
        return self.__category

    @property
    def event_type(self) -> TraceEventType:
        return self.__event_type

    @property
    def timestamp(self) -> int:
        return self.__tracing_clock_timestamp

    @property
    def pid(self) -> int:
        return self.__pid

    @property
    def tid(self) -> int:
        return self.__tid

    @property
    def uuid(self) -> int:
        return self.__uuid

    def __str__(self) -> str:
        return f"""{{
    name: {self.name}
    uuid: {self.uuid}
    cat: {self.category}
    ph: {self.event_type}
    ts: {self.timestamp}
    pid: {self.pid}
    tid: {self.tid}
}}
"""

    def __repr__(self) -> str:
        return f"{{ name={self.name}, uuid={self.uuid} }}"


class TEFReport(BaseReport, shorthand="TEF", file_type="json"):
    """Report class to access trace event format files."""

    class NameIDMapper(tp.List[str]):
        """Helper class to map name IDs to names."""

        def infer_name(self, name_id: int) -> str:
            return self[name_id]

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__name_id_mapper: TEFReport.NameIDMapper = TEFReport.NameIDMapper()
        try:
            self._parse_json()
        except Exception as e:
            print(f"Could not parse file: {self.path}")
            raise e
        # Parsing stackFrames is currently not implemented
        # x = data["stackFrames"]

    @property
    def timestamp_unit(self) -> str:
        return self.__timestamp_unit

    @property
    def trace_events(self) -> tp.List[TraceEvent]:
        return self.__trace_events

    @property
    def stack_frames(self) -> None:
        raise NotImplementedError(
            "Stack frame parsing is currently not implemented!"
        )

    def _patch_errors_from_file(self) -> None:
        with open(self.path, "r") as f:
            data = f.read()

        with open(self.path, "w") as f:
            remove_lost_events = re.compile('Lost \d+ events')
            for line in data.splitlines():
                if "Lost" in line:
                    LOG.error(
                        "Events where lost during tracing, patching json file."
                    )
                    line = remove_lost_events.sub("", line)

                f.write(line)

    def _parse_json(self) -> None:
        trace_events: tp.List[TraceEvent] = []

        self._patch_errors_from_file()

        with open(self.path, "rb") as f:
            parser = ijson.parse(f, use_float=True)
            trace_event: tp.Dict[str, str] = {}
            key = ""
            for prefix, event, value in parser:
                if event == "map_key":
                    key = value
                if prefix.startswith("traceEvents.item"):
                    if prefix == "traceEvents.item" and event == "start_map":
                        trace_event = {}
                    if prefix == "traceEvents.item" and event == "end_map":
                        if trace_event is not None:
                            if trace_event["name"] in self.__name_id_mapper:
                                name_id = self.__name_id_mapper.index(
                                    trace_event["name"]
                                )
                            else:
                                self.__name_id_mapper.append(
                                    trace_event["name"]
                                )
                                name_id = len(self.__name_id_mapper) - 1
                            trace_events.append(
                                TraceEvent(
                                    trace_event, name_id, self.__name_id_mapper
                                )
                            )

                    elif event == "string" or event == "number":
                        trace_event[key] = value
                elif prefix.startswith("timestampUnit"):
                    if event == "string":
                        self.__timestamp_unit: str = str(value)
        self.__trace_events: tp.List[TraceEvent] = trace_events


class TEFReportAggregate(
    ReportAggregate[TEFReport],
    shorthand=TEFReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple TEF reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReport)


__WORKLOAD_FILE_REGEX = re.compile(r"trace\_(?P<label>.+)$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    if (
        match :=
        __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    ):
        return str(match.group("label"))

    return None


class WorkloadSpecificTEFReportAggregate(
    WorkloadSpecificReportAggregate[TEFReport], shorthand="", file_type=""
):

    def __init__(self, path: Path) -> None:
        super().__init__(
            path,
            TEFReport,
            get_workload_label,
        )


def get_feature_performance_from_tef_report(
    tef_report: TEFReport,
) -> tp.Dict[str, int]:
    """Extract feature performance from a TEFReport."""
    open_events: tp.List[TraceEvent] = []

    feature_performances: tp.Dict[str, int] = {}

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

                end_timestamp = trace_event.timestamp
                begin_timestamp = opening_event.timestamp

                # Subtract feature duration from parent duration such that
                # it is not counted twice, similar to behavior in
                # Performance-Influence models.
                interactions = sorted([event.name for event in open_events])
                if open_events:
                    # Parent is equivalent to interaction of all open
                    # events.
                    interaction_string = get_interactions_from_fr_string(
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

                interaction_string = get_interactions_from_fr_string(
                    ",".join(sorted(interactions + [trace_event.name]))
                )

                current_performance = feature_performances.get(
                    interaction_string, 0
                )
                feature_performances[interaction_string] = (
                    current_performance + end_timestamp - begin_timestamp
                )

    if open_events:
        LOG.error("Not all events have been correctly closed.")
        LOG.debug(f"Events = {open_events}.")

    if found_missing_open_event:
        LOG.error("Not all events have been correctly opened.")

    return feature_performances


def get_interactions_from_fr_string(interactions: str, sep: str = ",") -> str:
    """Convert the feature strings in a TEFReport from FR(x,y) to x*y, similar
    to the format used by SPLConqueror."""
    interactions = (
        interactions.replace("FR", "").replace("(", "").replace(")", "")
    )

    interactions_list = interactions.split(sep)

    # Features cannot interact with itself, so remove duplicates
    interactions_list = list(set(interactions_list))

    interactions_list = sorted(interactions_list)

    # Ignore interactions with base, but do not remove base if it's the only
    # feature
    if "Base" in interactions_list and len(interactions_list) > 1:
        interactions_list.remove("Base")

    interactions_str = "*".join(interactions_list)

    return interactions_str

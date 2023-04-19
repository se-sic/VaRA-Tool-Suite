"""Report module to create and handle trace event format files, e.g., created
with chrome tracing."""

import re
import typing as tp
from enum import Enum
from pathlib import Path

import ijson

from varats.experiment.workload_util import WorkloadSpecificReportAggregate
from varats.report.report import BaseReport, ReportAggregate


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

    def __str__(self) -> str:
        return f"""{{
    name: {self.name}
    cat: {self.category}
    ph: {self.event_type}
    ts: {self.timestamp}
    pid: {self.pid}
    tid: {self.tid}
}}
"""

    def __repr__(self) -> str:
        return str(self)


class TEFReport(BaseReport, shorthand="TEF", file_type="json"):
    """Report class to access trace event format files."""

    class NameIDMapper(tp.List[str]):
        """Helper class to map name IDs to names."""

        def infer_name(self, name_id: int) -> str:
            return self[name_id]

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.__name_id_mapper: TEFReport.NameIDMapper = TEFReport.NameIDMapper()
        self._parse_json()
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

    def _parse_json(self) -> None:
        trace_events: tp.List[TraceEvent] = list()
        with open(self.path, "rb") as f:
            parser = ijson.parse(f)
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

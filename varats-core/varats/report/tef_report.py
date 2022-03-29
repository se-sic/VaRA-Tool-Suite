"""Report module to create and handle trace event format files, e.g., created
with chrome tracing."""

import json
import typing as tp
from enum import Enum
from pathlib import Path

from varats.report.report import BaseReport
from varats.report.report_aggregate import ReportAggregate


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

    def __init__(self, json_trace_event: tp.Dict[str, tp.Any]) -> None:
        self.__name = str(json_trace_event["name"])
        self.__category = str(json_trace_event["cat"])
        self.__event_type = TraceEventType.parse_event_type(
            json_trace_event["ph"]
        )
        self.__tracing_clock_timestamp = int(json_trace_event["ts"])
        self.__pid = int(json_trace_event["pid"])
        self.__tid = int(json_trace_event["tid"])

    @property
    def name(self) -> str:
        return self.__name

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

    def __init__(self, path: Path) -> None:
        super().__init__(path)

        with open(self.path, "r", encoding="utf-8") as json_tef_report:
            data = json.load(json_tef_report)

            self.__display_time_unit = str(data["displayTimeUnit"])
            self.__trace_events = self._parse_trace_events(data["traceEvents"])
            # Parsing stackFrames is currently not implemented
            # x = data["stackFrames"]

    @property
    def display_time_unit(self) -> str:
        return self.__display_time_unit

    @property
    def trace_events(self) -> tp.List[TraceEvent]:
        return self.__trace_events

    @property
    def stack_frames(self) -> None:
        raise NotImplementedError(
            "Stack frame parsing is currently not implemented!"
        )

    @staticmethod
    def _parse_trace_events(
        raw_event_list: tp.List[tp.Dict[str, tp.Any]]
    ) -> tp.List[TraceEvent]:
        return [TraceEvent(data_item) for data_item in raw_event_list]


class TEFReportAggregate(
    ReportAggregate[TEFReport],
    shorthand=TEFReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Manages multiple TEF reports in a zip archive."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReport)

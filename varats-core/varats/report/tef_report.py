"""Report module to create and handle trace event format files, e.g., created
with chrome tracing."""

import json
import typing as tp
from enum import Enum
from pathlib import Path
import numpy as np

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

    def __init__(self, json_trace_event: tp.Dict[str, tp.Any]) -> None:
        self.__name = str(json_trace_event["name"])
        self.__category = str(json_trace_event["cat"])
        self.__event_type = TraceEventType.parse_event_type(
            json_trace_event["ph"]
        )
        self.__tracing_clock_timestamp = int(json_trace_event["ts"])
        self.__pid = int(json_trace_event["pid"])
        self.__tid = int(json_trace_event["tid"])
        self.__args_id = int(json_trace_event["args"]["ID"])

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

    @property
    def args_id(self):
        return self.__args_id

    def __str__(self) -> str:
        return f"""{{
    name: {self.name}
    cat: {self.category}
    ph: {self.event_type}
    ts: {self.timestamp}
    pid: {self.pid}
    tid: {self.tid}
    args: {self.args_id}
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
            print("Visiting the TEFReport")
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

    def feature_time_accumulator(self):
        print("Calls accumulator")
        # Feature_dict contains a list of all measurements for each feature
        feature_dict = dict()

        # time_dict takes an argument ID and maps it to the beginning time
        time_dict = dict()
        # id maps id to the feature name
        id_dict = dict()
        for trace_event in self.trace_events:
            if feature_dict.get(trace_event.name) is None:
                feature_dict.setdefault(trace_event.name, [])
            if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                id_dict[trace_event.args_id] = trace_event.name
                time_dict[trace_event.args_id] = trace_event.timestamp
                print(str(trace_event.args_id) + "\n")
            elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                # Trace Event with same Arg ID found, update time in time_dict from beginning to total time taken for that event
                print(str(trace_event.args_id) + "\n")
                time_dict[trace_event.args_id] = trace_event.timestamp - time_dict[trace_event.args_id]
            #ToDo raise error for unexpcted event type

        with open("/scratch/messerig/varaRoot/results/xz/xzWhiteBoxTest/jsonTest.json", "w", encoding="utf-8") as file:
            result_dict = dict()
            for args_id in id_dict.keys():
                # We add for every ID the time it takes for that process to finish, to the list of durations
                # associated with the respective feature
                feature_dict[id_dict[args_id]] = feature_dict[id_dict[args_id]].append(time_dict[args_id])

            for name in feature_dict.keys():
                tmp_dict = dict()
                tmp_dict["Occurrences"] = len(feature_dict[name])
                tmp_dict["Overall Time"] = (np.sum(feature_dict[name]))/1000
                tmp_dict["Mean"] = (np.mean(feature_dict[name]))/1000
                tmp_dict["Variance"] = (np.var(feature_dict[name]))/1000
                tmp_dict["Standard Deviation"] = (np.std(feature_dict[name]))/1000
                # file.write(f"Number of occurrences {name}: {len(feature_dict[name])}\n")
                # file.write(f"Overall Time of feature {name}: {np.sum(feature_dict[name])}\n")
                # file.write(f"Mean of feature {name}: {np.mean(feature_dict[name])}\n")
                # file.write(f"Variance of Feature {name}: {np.var(feature_dict[name])}\n")
                # file.write(f"Standard Deviation of Feature {name}: {np.std(feature_dict[name])}")
                result_dict[name] = tmp_dict
            json.dump(result_dict, file)

class TEFReportAggregate(
    ReportAggregate[TEFReport],
    shorthand=TEFReport.SHORTHAND + ReportAggregate.SHORTHAND,
    file_type=ReportAggregate.FILE_TYPE
):
    """Context Manager for parsing multiple TEF reports stored inside a zip
    file."""

    def __init__(self, path: Path) -> None:
        super().__init__(path, TEFReport)

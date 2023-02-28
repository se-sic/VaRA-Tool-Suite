"""Report module to create and handle trace event format files, e.g., created
with chrome tracing."""

import json

import re
import typing as tp
from enum import Enum
from pathlib import Path
import numpy as np

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

#    def __init__(self, json_trace_event: tp.Dict[str, tp.Any]) -> None:
#        self.__name = str(json_trace_event["name"])
#        self.__name = self.__name.replace("FR(", "")
#        if self.__name[-1] == ")":
#            self.__name = self.__name[:-1]

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
        self.__args_id = int(json_trace_event["ID"])

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
    def args_id(self) -> int:
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

    class NameIDMapper(tp.List[str]):
        """Helper class to map name IDs to names."""

        def infer_name(self, name_id: int) -> str:
            return self[name_id]

#            if "displayTimeUnit" in data:
#                self.__display_time_unit = str(data["displayTimeUnit"])
#            if "traceEvents" in data:
#                self.__trace_events = self._parse_trace_events(data["traceEvents"])

            # Parsing stackFrames is currently not implemented
            # x = data["stackFrames"]
#            print("Visiting the TEFReport")
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
                            
                            name = trace_event["name"]
                            name = name.replace("FR(", "")
                            if name[-1] == ")":
                                name = name[:-1]
                                
                            if trace_event["name"] in self.__name_id_mapper:
                                name_id = self.__name_id_mapper.index(
                                    trace_event["name"]
                                )
                            else:
                                self.__name_id_mapper.append(
                                    name
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

    # Gets the current_feature list and return a string of all features concatenated
    # Contains no duplicate and alphabetical sorted
    @staticmethod
    def features_to_string(current_feature:tp.List[str]) -> str:
        tmp_list = current_feature
        alphabet_list = list()
        tmp_set = set()
        result = ""
        for feature_list in tmp_list:
            for feature in feature_list:
                tmp_set.add(feature)
        for feature in tmp_set:
            alphabet_list.append(feature)
        alphabet_list.sort()
        for feature in alphabet_list:
            result += feature + ","
        result = result[:-1]
        return result

    def feature_time_accumulator(self, path:Path) -> None:
        # feature_dict contains a list of all measurements for each feature
        feature_dict:tp.Dict[list[str],list[float]] = dict()
        # id_dict maps id to current occurrences of that id
        id_dict:tp.Dict[int, int] = dict()
        # current_active_feature is a list of lists, containing lists of features for a active process
        current_active_feature:tp.List[str] = list()
        for trace_event in self.trace_events:
            if feature_dict.get(trace_event.name) is None:
                feature_dict.setdefault(trace_event.name, list())
            if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                if id_dict.get(trace_event.args_id) is None:
                    id_dict.setdefault(trace_event.args_id, 0)
                id_dict[trace_event.args_id] = id_dict[trace_event.args_id] + 1
                current_feature = trace_event.name.split(",")
                if current_feature in current_active_feature:
                    continue
                # When adding a new feature to the current list we end the previous running feature
                feature_string = self.features_to_string(current_active_feature)
                if len(current_active_feature) != 0:
                    feature_dict[feature_string][-1] \
                        = abs(trace_event.timestamp - feature_dict[feature_string][-1])

                current_active_feature.append(current_feature)
                feature_string = self.features_to_string(current_active_feature)

                if feature_dict.get(feature_string) is None:
                    feature_dict.setdefault(feature_string, list())
                feature_dict[feature_string].append(trace_event.timestamp)

            elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                current_feature = trace_event.name.split(",")
                feature_string = self.features_to_string(current_active_feature)

                # Trace Event with same Arg ID found, update time in
                # time_dict from beginning to total time taken for that event
                if id_dict.get(trace_event.args_id) is None:
                    print(str(trace_event.args_id) + " \n")
                    continue
                # If an Event ended more often then it started its invalid
                elif id_dict[trace_event.args_id] > 0:
                    id_dict[trace_event.args_id] = id_dict[trace_event.args_id] - 1
                else:
                    continue

                # List[-1] returns last element of the list
                feature_dict[feature_string][-1] = abs(trace_event.timestamp - feature_dict[feature_string][-1])

                if current_feature in current_active_feature:
                    current_active_feature.remove(current_feature)
                # ToDo Raise exception feature not in current feature list but is suppose to end

                if len(current_active_feature) > 0:
                    feature_dict[self.features_to_string(current_active_feature)].append(trace_event.timestamp)
            # ToDo raise error for unexpcted event type

        with open(path , "w", encoding="utf-8") as file:
            result_dict = dict()
            overall_time = 0

            for name in feature_dict.keys():
                if len(feature_dict[name]) == 0:
                    continue
                tmp_dict = dict()
                tmp_dict["Occurrences"] = len(feature_dict[name])
                tmp_dict["Overall Time"] = (np.sum(feature_dict[name])) / 1000
                tmp_dict["Mean"] = (np.mean(feature_dict[name])) / 1000
                tmp_dict["Variance"] = (np.var(feature_dict[name])) / 1000
                tmp_dict["Standard Deviation"] = (np.std(feature_dict[name])) / 1000
                result_dict[name] = tmp_dict
                overall_time += (np.sum(feature_dict[name])) / 1000

            tmp_time_dict = dict()
            tmp_time_dict["Time Taken"] = overall_time
            result_dict["Overall time for all features"] = tmp_time_dict
            #header_dict = dict()
            #header_dict["Results parsed"] = result_dict
            json.dump(result_dict, file)


    @staticmethod
    def wall_clock_times(path:Path) -> None:
        result_dict = dict()
        number_of_repetitions = 0
        for report in path.iterdir():
            with open(report) as f:
                number_of_repetitions += 1
                data = json.load(f)
                for feature in data:
                    if feature not in result_dict:
                        result_dict[feature] = dict()
                    for elements in data[feature]:
                        if data[feature][elements] not in result_dict[feature]:
                            result_dict[feature][elements] = list()
                        result_dict[feature][elements].append(data[feature][elements])

        tmp_dict = dict()
        tmp_dict["Repetitions"] = number_of_repetitions
        for feature in result_dict:
            for elements in result_dict[feature]:
                result_dict[feature][elements] = np.sum(result_dict[feature][elements]) / len(result_dict[feature][elements])
        result_dict["Number of Repetitions"] = tmp_dict


        with open(path / "result_aggregate.json" , "w", encoding="utf-8") as json_result_file:
            json.dump(result_dict, json_result_file)

__WORKLOAD_FILE_REGEX = re.compile(r"trace\_(?P<label>.+)$")


def get_workload_label(workload_specific_report_file: Path) -> tp.Optional[str]:
    match = __WORKLOAD_FILE_REGEX.search(workload_specific_report_file.stem)
    if match:
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

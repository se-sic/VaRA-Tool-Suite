"""Trace file utilities."""
import json
import typing as tp
from collections import OrderedDict
from pathlib import Path


def __timestamp(event: tp.OrderedDict[str, tp.Any]) -> float:
    return float(event["ts"])


def sanitize_trace(path: Path,
                   category: tp.Optional[str] = None,
                   tid: int = 0) -> tp.OrderedDict[str, tp.Any]:
    """Read and clean up a trace file."""
    trace_events: tp.List[tp.OrderedDict[str, tp.Any]] = []
    with open(path, mode="r", encoding="UTF-8") as file:
        for event in json.load(file)["traceEvents"]:
            item: tp.OrderedDict[str, tp.Any] = OrderedDict()
            item["name"] = event["name"]
            item["ph"] = event["ph"]
            item["ts"] = float(event["ts"])
            item["pid"] = int(event["pid"])
            item["tid"] = tid + int(event["tid"])

            if category:
                if "cat" in event:
                    item["cat"] = f"{category}: {event['cat']}"
                else:
                    item["cat"] = category
            else:
                if "cat" in event:
                    item["cat"] = event["cat"]

            if "args" in event:
                item["args"] = event["args"]

            trace_events.append(item)

    trace_events.sort(key=__timestamp)

    if trace_events:
        start = trace_events[0]["ts"]
        for event in trace_events:
            event["ts"] -= start

    result: tp.OrderedDict[str, tp.Any] = OrderedDict()
    result["traceEvents"] = trace_events
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result


def merge_trace(
    *traces: tp.Union[tp.Tuple[Path, str], tp.Tuple[Path, str, int]]
) -> tp.OrderedDict[str, tp.Any]:
    """Merge multiple files into a single trace."""
    trace_events: tp.List[tp.OrderedDict[str, tp.Any]] = []
    for trace in traces:
        trace_events += sanitize_trace(*trace)["traceEvents"]

    trace_events.sort(key=__timestamp)

    result: tp.OrderedDict[str, tp.Any] = OrderedDict()
    result["traceEvents"] = trace_events
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result

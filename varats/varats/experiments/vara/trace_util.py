"""Trace file utilities."""
import json
import typing as tp
from collections import OrderedDict
from pathlib import Path


def sanitize_trace(path: Path, category: str) -> tp.OrderedDict[str, tp.Any]:
    """Read and clean up a trace file."""
    trace_events: tp.List[tp.OrderedDict[str, tp.Any]] = []
    with open(path, mode="r", encoding="UTF-8") as file:
        for event in json.load(file)["traceEvents"]:
            item: tp.OrderedDict[str, tp.Any] = OrderedDict()
            item["name"] = event["name"]
            item["ph"] = event["ph"]
            item["ts"] = int(float(event["ts"]))
            item["pid"] = int(event["pid"])
            item["tid"] = int(event["tid"])

            if "cat" in event:
                item["cat"] = f"{category}: {event['cat']}"
            else:
                item["cat"] = category

            if "args" in event:
                item["args"] = event["args"]

            trace_events.append(item)

    trace_events.sort(key=lambda x: x["ts"])

    # # try to fix missing events
    # missing: tp.OrderedDict[str, tp.Any] = OrderedDict()
    # start, end = trace_events[0]["ts"], trace_events[-1]["ts"]
    # for event in trace_events:
    #     event["ts"] -= start
    #     name = event["name"]
    #     if name in missing:
    #         del missing[name]
    #     else:
    #         missing[name] = event
    #
    # for event in reversed(missing.values()):
    #     item: tp.OrderedDict[str, tp.Any] = OrderedDict()
    #     item["name"] = event["name"]
    #     item["ph"] = "E"
    #     item["ts"] = end - start,
    #     item["pid"] = event["pid"]
    #     item["tid"] = event["tid"]
    #     item["cat"] = event['cat']
    #     trace_events.append(item)

    result: tp.OrderedDict[str, tp.Any] = OrderedDict()
    result["traceEvents"] = trace_events
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result


def merge_trace(*traces) -> tp.OrderedDict[str, tp.Any]:
    """Merge multiple files into a single trace."""
    trace_events: tp.List[tp.OrderedDict[str, tp.Any]] = []
    for trace in traces:
        trace_events += sanitize_trace(*trace)["traceEvents"]
    result: tp.OrderedDict[str, tp.Any] = OrderedDict()
    result["traceEvents"] = sorted(trace_events, key=lambda x: x["ts"])
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result

"""TODO."""
import json
import typing
from collections import OrderedDict
from pathlib import Path


def sanitize_trace(path: Path, category: str) -> OrderedDict:
    """TODO."""
    trace_events = []
    with open(path, mode="r", encoding="UTF-8") as file:
        for event in json.load(file)["traceEvents"]:
            item: typing.Dict = {
                "name": event["name"],
                "ph": event["ph"],
                "ts": int(float(event["ts"])),
                "pid": int(event["pid"]),
                "tid": int(event["tid"]),
            }

            if "cat" in event:
                item["cat"] = f"{category}: {event['cat']}"
            else:
                item["cat"] = category

            if "args" in event:
                item["args"] = event["args"]

            trace_events.append(item)

    trace_events.sort(key=lambda i: i["ts"])

    missing: OrderedDict = OrderedDict()
    start, end = trace_events[0]["ts"], trace_events[-1]["ts"]
    for event in trace_events:
        event["ts"] -= start
        name = event["name"]
        if name in missing:
            del missing[name]
        else:
            missing[name] = event

    for event in reversed(missing.values()):
        trace_events.append({
            "name": event["name"],
            "ph": "E",
            "ts": end - start,
            "pid": event["pid"],
            "tid": event["tid"],
            "cat": f"{event['cat']} (Missing)"
        })

    result: OrderedDict = OrderedDict()
    result["traceEvents"] = trace_events
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result


def merge_trace(*traces) -> OrderedDict:
    """TODO."""
    trace_events = []
    for trace in traces:
        trace_events += sanitize_trace(*trace)["traceEvents"]
    result: OrderedDict = OrderedDict()
    result["traceEvents"] = sorted(trace_events, key=lambda i: i["ts"])
    result["stackFrames"] = {}
    result["timestampUnit"] = "us"
    return result

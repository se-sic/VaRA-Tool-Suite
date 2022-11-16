"""Test VaRA trace utilities."""
import json
import tempfile
import unittest
from pathlib import Path

from varats.experiment.trace_util import merge_trace, sanitize_trace

TRACE_1 = {
    "traceEvents": [{
        "name": "main",
        "ph": "B",
        "tid": "42",
        "pid": "42",
        "ts": "0.1",
        "sf": "0"
    }, {
        "name": "foo(int)",
        "ph": "B",
        "tid": "42",
        "pid": "42",
        "ts": "0.9",
        "sf": "1"
    }, {
        "name": "foo(int)",
        "ph": "E",
        "tid": "42",
        "pid": "42",
        "ts": "2",
        "sf": "1"
    }, {
        "name": "main",
        "ph": "E",
        "tid": "42",
        "pid": "42",
        "ts": "2.99",
        "sf": "0"
    }],
    "displayTimeUnit": "ns",
    "stackFrames": {
        "0": {
            "name": "main"
        },
        "1": {
            "name": "foo(int)",
            "parent": "0"
        }
    }
}

TRACE_1_SANITIZED = {
    "traceEvents": [{
        "name": "main",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
    }, {
        "name": "foo(int)",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
    }, {
        "name": "foo(int)",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
    }, {
        "name": "main",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
    }],
    "stackFrames": {},
    "timestampUnit": "us"
}

TRACE_2 = {
    "traceEvents": [{
        "name": "Base",
        "cat": "Feature",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
        "args": {
            "ID": 0
        }
    }, {
        "name": "FR(Foo)",
        "cat": "Feature",
        "ph": "B",
        "ts": 1,
        "pid": 42,
        "tid": 42,
        "args": {
            "ID": 1337
        }
    }, {
        "name": "FR(Foo)",
        "cat": "Feature",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
        "args": {
            "ID": 1337
        }
    }, {
        "name": "Base",
        "cat": "Feature",
        "ph": "E",
        "ts": 3,
        "pid": 42,
        "tid": 42,
        "args": {
            "ID": 0
        }
    }],
    "stackFrames": {},
    "timestampUnit": "us"
}

TRACE_2_SANITIZED = {
    "traceEvents": [{
        "name": "Base",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
        "cat": "Feature",
        "args": {
            "ID": 0
        }
    }, {
        "name": "FR(Foo)",
        "ph": "B",
        "ts": 1,
        "pid": 42,
        "tid": 42,
        "cat": "Feature",
        "args": {
            "ID": 1337
        }
    }, {
        "name": "FR(Foo)",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
        "cat": "Feature",
        "args": {
            "ID": 1337
        }
    }, {
        "name": "Base",
        "ph": "E",
        "ts": 3,
        "pid": 42,
        "tid": 42,
        "cat": "Feature",
        "args": {
            "ID": 0
        }
    }],
    "stackFrames": {},
    "timestampUnit": "us"
}

MERGED = {
    "traceEvents": [{
        "name": "main",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 1"
    }, {
        "name": "foo(int)",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 1"
    }, {
        "name": "Base",
        "ph": "B",
        "ts": 0,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 2: Feature",
        "args": {
            "ID": 0
        }
    }, {
        "name": "FR(Foo)",
        "ph": "B",
        "ts": 1,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 2: Feature",
        "args": {
            "ID": 1337
        }
    }, {
        "name": "foo(int)",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 1"
    }, {
        "name": "main",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 1"
    }, {
        "name": "FR(Foo)",
        "ph": "E",
        "ts": 2,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 2: Feature",
        "args": {
            "ID": 1337
        }
    }, {
        "name": "Base",
        "ph": "E",
        "ts": 3,
        "pid": 42,
        "tid": 42,
        "cat": "Trace 2: Feature",
        "args": {
            "ID": 0
        }
    }],
    "stackFrames": {},
    "timestampUnit": "us"
}


class TestTraceUtil(unittest.TestCase):

    def test_sanitize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            setup = [
                {
                    "raw": TRACE_1,
                    "sanitized": TRACE_1_SANITIZED,
                    "path": Path(tmp_dir) / f"trace_1_raw.json"
                },
                {
                    "raw": TRACE_1_SANITIZED,
                    "sanitized": TRACE_1_SANITIZED,
                    "path": Path(tmp_dir) / f"trace_1_sanitized.json"
                },
                {
                    "raw": TRACE_2,
                    "sanitized": TRACE_2_SANITIZED,
                    "path": Path(tmp_dir) / f"trace_2_raw.json"
                },
                {
                    "raw": TRACE_2_SANITIZED,
                    "sanitized": TRACE_2_SANITIZED,
                    "path": Path(tmp_dir) / f"trace_2_sanitized.json"
                },
            ]
            for trace in setup:
                with open(trace["path"], "w") as file:
                    file.write(json.dumps(trace["raw"], sort_keys=True))
                self.assertDictEqual(
                    trace["sanitized"], sanitize_trace(trace["path"])
                )

    def test_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            setup = [
                {
                    "raw": TRACE_1,
                    "path": Path(tmp_dir) / f"trace_1.json"
                },
                {
                    "raw": TRACE_2,
                    "path": Path(tmp_dir) / f"trace_2.json"
                },
            ]
            for trace in setup:
                with open(trace["path"], "w") as file:
                    file.write(json.dumps(trace["raw"], sort_keys=True))
            self.assertDictEqual(
                MERGED,
                merge_trace(
                    (setup[0]["path"], "Trace 1"),
                    (setup[1]["path"], "Trace 2"),
                )
            )

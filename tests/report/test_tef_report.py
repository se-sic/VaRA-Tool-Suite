"""Test TEFReport."""

import json
import unittest
from pathlib import Path
from unittest import mock

from varats.report.tef_report import TEFReport, TraceEvent, TraceEventType

TRACE_EVENT_FORMAT_OUTPUT = """{
    "traceEvents": [{
        "name": "Base",
        "cat": "Feature",
        "ph": "B",
        "ts": 1637675320727304236,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Foo",
        "cat": "Feature",
        "ph": "B",
        "ts": 1637675320727316656,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Foo",
        "cat": "Feature",
        "ph": "E",
        "ts": 1637675325727410375,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Bar",
        "cat": "Feature",
        "ph": "B",
        "ts": 1637675328727504858,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Bar",
        "cat": "Feature",
        "ph": "E",
        "ts": 1637675331727788401,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Foo_2",
        "cat": "Feature",
        "ph": "B",
        "ts": 1637675335727890982,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Foo_2",
        "cat": "Feature",
        "ph": "E",
        "ts": 1637675341728002649,
        "pid": 91098,
        "tid": 91098
    }, {
        "name": "Base",
        "cat": "Feature",
        "ph": "E",
        "ts": 1637675341728008439,
        "pid": 91098,
        "tid": 91098
    } ],
    "displayTimeUnit": "ns",
    "stackFrames": {}
}
"""


class TestTraceEventType(unittest.TestCase):
    """Test if we can correclty parse TraceEventTypes."""

    def test_parse_duration_events(self) -> None:
        """Test if we correctly parse duration event types."""
        self.assertEqual(
            TraceEventType.parse_event_type("B"),
            TraceEventType.DURATION_EVENT_BEGIN
        )
        self.assertEqual(
            TraceEventType.parse_event_type("E"),
            TraceEventType.DURATION_EVENT_END
        )

    def test_parse_async_events(self) -> None:
        """Test if we correctly parse async event types."""
        self.assertEqual(
            TraceEventType.parse_event_type("b"),
            TraceEventType.ASYNC_EVENT_START
        )
        self.assertEqual(
            TraceEventType.parse_event_type("n"),
            TraceEventType.ASYNC_EVENT_INSTANT
        )
        self.assertEqual(
            TraceEventType.parse_event_type("e"), TraceEventType.ASYNC_EVENT_END
        )

    def test_parse_flow_events(self) -> None:
        """Test if we correctly parse flow event types."""
        self.assertEqual(
            TraceEventType.parse_event_type("s"),
            TraceEventType.FLOW_EVENT_START
        )
        self.assertEqual(
            TraceEventType.parse_event_type("t"), TraceEventType.FLOW_EVENT_STEP
        )
        self.assertEqual(
            TraceEventType.parse_event_type("f"), TraceEventType.FLOW_EVENT_END
        )

    def test_parse_other_events(self) -> None:
        """Test if we correctly parse other event types."""
        self.assertEqual(
            TraceEventType.parse_event_type("X"), TraceEventType.COMPLETE_EVENT
        )
        self.assertEqual(
            TraceEventType.parse_event_type("i"), TraceEventType.INSTANT_EVENT
        )
        self.assertEqual(
            TraceEventType.parse_event_type("C"), TraceEventType.COUNTER_EVENT
        )
        self.assertEqual(
            TraceEventType.parse_event_type("P"), TraceEventType.SAMPLE_EVENT
        )

    def test_fail_at_wrong_event_string(self) -> None:
        """Test if we fail should an event type not match."""
        self.assertRaises(LookupError, TraceEventType.parse_event_type, "42")
        self.assertRaises(LookupError, TraceEventType.parse_event_type, "I")
        self.assertRaises(LookupError, TraceEventType.parse_event_type, "D")
        self.assertRaises(LookupError, TraceEventType.parse_event_type, "d")


SINGLE_TRACE_EVENT = """{
    "name": "Base",
    "cat": "Feature",
    "ph": "E",
    "ts": 1637675341728008439,
    "pid": 91098,
    "tid": 91099
}
"""


class TestTraceEvent(unittest.TestCase):
    """Test if we can correctly load trace events and parse values."""

    trace_event: TraceEvent

    @classmethod
    def setUpClass(cls):
        """Load trace event."""
        cls.trace_event = TraceEvent(json.loads(SINGLE_TRACE_EVENT))

    def test_name_parsing(self):
        """Test if we can correctly parse event names."""
        self.assertEqual(self.trace_event.name, "Base")
        self.assertNotEqual(self.trace_event.name, "Foo")

    def test_category_parsing(self):
        """Test if we can correctly parse event categories."""
        self.assertEqual(self.trace_event.category, "Feature")
        self.assertNotEqual(self.trace_event.name, "Foo")

    def test_event_type_parsing(self):
        """Test if we can correctly parse event type."""
        self.assertEqual(
            self.trace_event.event_type, TraceEventType.DURATION_EVENT_END
        )
        self.assertIsInstance(self.trace_event.event_type, TraceEventType)
        self.assertNotEqual(
            self.trace_event.event_type, TraceEventType.DURATION_EVENT_BEGIN
        )

    def test_timestamp_parsing(self):
        """Test if we can correctly parse event timestamps."""
        self.assertEqual(self.trace_event.timestamp, 1637675341728008439)
        self.assertIsInstance(self.trace_event.timestamp, int)

        self.assertNotEqual(self.trace_event.name, 1637675341728008438)
        self.assertNotEqual(self.trace_event.name, 0)

    def test_pid_parsing(self):
        """Test if we can correctly parse event pid."""
        self.assertEqual(self.trace_event.pid, 91098)
        self.assertIsInstance(self.trace_event.pid, int)

        self.assertNotEqual(self.trace_event.name, 91099)
        self.assertNotEqual(self.trace_event.name, 91097)
        self.assertNotEqual(self.trace_event.name, 0)

    def test_tid_parsing(self):
        """Test if we can correctly parse event tid."""
        self.assertEqual(self.trace_event.tid, 91099)
        self.assertIsInstance(self.trace_event.tid, int)

        self.assertNotEqual(self.trace_event.name, 91100)
        self.assertNotEqual(self.trace_event.name, 91098)
        self.assertNotEqual(self.trace_event.name, 0)


class TestTEFReportParser(unittest.TestCase):
    """Tests if the trace-event-format report can be parsed correctly."""

    report: TEFReport

    @classmethod
    def setUpClass(cls):
        """Load and prepare TEF report."""
        with mock.patch(
            'builtins.open',
            new=mock.mock_open(read_data=TRACE_EVENT_FORMAT_OUTPUT)
        ):
            cls.report = TEFReport(Path("fake_file_path"))

    def test_parse_time_unit(self) -> None:
        """Test if the time unit field is correclty parsed."""
        self.assertEqual(self.report.display_time_unit, "ns")
        self.assertNotEqual(self.report.display_time_unit, "ms")

    def test_parse_trace_events(self) -> None:
        """Test if we correctly parse the listed trace events."""
        self.assertEqual(len(self.report.trace_events), 8)

        self.assertEqual(self.report.trace_events[0].name, "Base")

    def test_parse_stack_frames(self) -> None:
        """Test if we correctly parse stack frames."""
        # Currently, not implemented so we should get an exception.
        with self.assertRaises(NotImplementedError):
            _ = self.report.stack_frames

"""Report that simply takes the output of an phasar analysis."""

from varats.report.report import BaseReport


class EnvTraceReport(BaseReport, shorthand="ENV-TRACE", file_type="json"):
    """The phasar report produces json files with the output for each file."""

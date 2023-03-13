"""Module for FeatureTracingStatsReport."""

from varats.report.report import BaseReport


class FeatureTracingStatsReport(BaseReport, shorthand="FTS", file_type="txt"):
    """Output of VaRA's bpftrace script 'UsdtExecutionStats.bt', which provides
    execution statistics about events during tracing."""

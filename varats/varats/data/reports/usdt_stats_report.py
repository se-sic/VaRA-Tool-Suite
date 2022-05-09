"""Implements report for VaRA's bpftrace script 'UsdtExecutionStats.bt'."""

from varats.report.report import BaseReport


class VaraInstrumentationStatsReport(
    BaseReport, shorthand="IS", file_type="txt"
):
    """Report for VaRA's bpftrace script 'UsdtExecutionStats.bt', which provides
    execution information of instrumentation."""

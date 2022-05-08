"""Implements report for VaRA's bpftrace script 'UsdtExecutionStats.bt'."""

from varats.report.report import BaseReport


class VaraUsdtStatsReport(BaseReport, shorthand="VaraUS", file_type="txt"):
    """Report for VaRA's bpftrace script 'UsdtExecutionStats.bt', which provides
    information about the instrumented markers during execution."""

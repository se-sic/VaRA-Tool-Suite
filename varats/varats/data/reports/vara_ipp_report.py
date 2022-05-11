"""Implements report for VaRA's InstrumentationPointPrinter utility pass."""

from varats.report.report import BaseReport


class VaraIPPReport(BaseReport, shorthand="VaraIPP", file_type="txt"):
    """Report for VaRA's InstrumentationPointPrinter utility pass, which prints
    the source code locations of instrumentation points of feature regions."""

"""Implements report for VaRA's InstrumentationPointPrinter utility pass."""

from varats.report.report import BaseReport


class VaraFRIDPPReport(BaseReport, shorthand="VaraFRIDPP", file_type="txt"):
    """Report for VaRA's FuncRelativeIDPrinter utility pass, which prints the
    source code locations of instrumentation points of feature regions."""

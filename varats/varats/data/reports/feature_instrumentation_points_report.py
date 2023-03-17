"""Report for VaRA's InstrumentationPointPrinter utility pass."""

from varats.report.report import BaseReport


class FeatureInstrumentationPointsReport(
    BaseReport, shorthand="FIP", file_type="txt"
):
    """Report for VaRA's InstrumentationPointPrinter utility pass, which prints
    information about the instrumentation points of feature regions."""

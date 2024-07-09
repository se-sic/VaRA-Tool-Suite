from varats.report.report import BaseReport, ReportAggregate


class RuntimeFeatureInstrReport(BaseReport, shorthand="RFI", file_type="txt"):
    """Report for VaRA's InstrumentationPointPrinter utility pass, which prints
    information about the instrumentation points of feature regions."""
    pass


class RunTimeFeatureInstrAggReport(
    ReportAggregate[RuntimeFeatureInstrReport],
    shorthand="RFI_AGG",
    file_type="zip"
):
    """Report for VaRA's InstrumentationPointPrinter utility pass, which prints
    information about the instrumentation points of feature regions."""
    pass

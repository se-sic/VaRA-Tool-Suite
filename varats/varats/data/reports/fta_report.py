"""Module for FTAReport."""

from varats.report.report import BaseReport


class FTAReport(BaseReport, shorthand="FTAR", file_type="txt"):
    """
    Report for the feature taint analysis.

    Nothing gets printed into the report yet and the result file has no file
    type.
    """

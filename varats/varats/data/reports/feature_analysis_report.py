"""Module for FTAReport."""

from varats.report.report import BaseReport


class FeatureAnalysisReport(BaseReport, shorthand="FAR", file_type="yaml"):
    """
    Report for the feature taint analysis.

    Nothing gets printed into the report yet and the result file has no file
    type.
    """
